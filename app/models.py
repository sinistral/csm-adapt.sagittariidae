
import hashids
import json
import re
import sqlalchemy.types as types

from sqlalchemy                import ForeignKey, Column, String, Text, Integer
from sqlalchemy                import event
from sqlalchemy.exc            import OperationalError, IntegrityError
from sqlalchemy.orm            import Session
from sqlalchemy.orm            import relationship
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.exc        import NoResultFound, MultipleResultsFound
from urllib                    import quote

from app import app, db


BAD_URI_PAT  = re.compile("%.{2}|\/|_")
COLLAPSE_PAT = re.compile("-{2,}")


@event.listens_for(Session, 'after_flush_postexec')
def inject_obfuscated_id_after_flush_postexec(session, flush_context):
    def inject_obfuscated_id(m):
        if m.obfuscated_id is None:
            m.obfuscated_id = m.__hashidgen__.encode(m.id)
        return m
    return [inject_obfuscated_id(m) for m in session.identity_map.values()]


def with_transaction(session, f):
    """
    Execute `f` in a DB transaction.  If `f` completes successfully, the
    transaction is committed, otherwise an error is raised and the transaction
    is rolled back.

    `f` must accept a single argument: the database session instance.
    """
    try:
        f(session)
        session.commit()
    except Exception, e:
        session.rollback()
        raise e


def uri_name(name):
    """
    Convert the name of a resource (like a project or sample) into a
    URI-friendly form.  This function has strong opinions about what a "good"
    URI ID is, and will complain if the ID cannot be rendered in an acceptable
    form.  In particular, it should not contain any characters that need to be
    escaped; cf. `urllib.quote()`.
    """
    # URI-escape special characters
    new_name = quote(name.lower().replace(" ", "-"))
    # Convert escapes into underscores; i.e. foo%20bar -> foo-bar
    new_name = re.sub(BAD_URI_PAT, '-', new_name)
    # Collapse multiple consecutive hyphens; i.e. foo---bar -> foo-bar
    new_name = re.sub(COLLAPSE_PAT, '-', new_name)
    # And return our pretty new identifier
    return new_name


def dictify(model):
    """
    Return a model as a dictionary. 'Private' attributes are removed and
    underscores are replaced with more hyphens in attribute names, making for
    more aesthetically pleasing HTTP data maps.
    """
    assert hasattr(model, 'id')
    assert model.id is not None, 'Model\'s ID may not be None'
    assert hasattr(model, 'obfuscated_id')
    assert model.obfuscated_id is not None, 'Model\'s obfuscated ID may not be None'

    def tr(kv):
        return (kv[0].replace('_', '-'), kv[1])
    d = dict(tr(kv) for kv in iter(model.__dict__.items())
             if not kv[0].startswith('_'))
    if d.has_key('name'):
        d['id'] = '-'.join([d['obfuscated-id'], uri_name(d['name'])])
    else:
        d['id'] = d['obfuscated-id']
    del d['obfuscated-id']
    return d


def jsonize_models(models):
    """Return a list of model instances as a JSON array."""
    return json.dumps([dictify(m) for m in models])


def jsonize_model(model):
    """Return a single model instance as a JSON object."""
    return json.dumps(dictify(model))


class HashIds(hashids.Hashids):
    """
    HashID generator for our resources.  Database-assigned IDs are
    hashed/obfuscated to avoid leaking implementation details and creating
    unintentional expectations around resource identification.q
    cf. http://hashids.org
    """
    def __init__(self, salt, min_length=5):
        super(HashIds, self).__init__(
            salt=';'.join(['sagittarius', salt]),
            min_length=min_length)


class Representable:
    """
    A base class for Models that generically generates a String representation
    of the model and its properties.
    """
    def __repr__(self):
        def repr_attr(k):
            return '%s=%s' % (k, getattr(self, k))
        reprified_attrs = [repr_attr(k) for k in iter(sorted(self.__dict__.keys()))
                           if not k.startswith('_')]
        if len(reprified_attrs) == 0:
            attrs_repr = '<no instance attributes>'
        else:
            attrs_repr = ', '.join(reprified_attrs)
        return '<%s: %s>' % (self.__class__.__name__, attrs_repr)


class ResourceMetaClass(type(db.Model)):
    """
    A metaclass that injects the identifier fields that should be present on
    all Models.
    """
    def __new__(metacls, clsname,  parents, attrs):
        attrs['id'] = Column(Integer, primary_key=True)
        attrs['obfuscated_id'] = Column(String(15), unique=True)
        return super(ResourceMetaClass, metacls).__new__(
            metacls, clsname, (Representable,) + parents, attrs)


class Project(db.Model):
    __metaclass__ = ResourceMetaClass
    __tablename__ = 'project'
    __hashidgen__ = HashIds('Project')

    name = Column(String(80), unique=True)
    sample_mask = Column(String(64), unique=False)
    # objects forward-related to project
    samples = relationship(
        'Sample', backref='project', lazy='dynamic')


def get_projects():
    """
    Returns a JSON array of projects.
    """
    try:
        projects = Project.query.all()
    except OperationalError:
        return ''
    return jsonize_models(projects)


def add_project(name, sample_mask):
    """
    Adds a new project.
    """
    try:
        _ = Project.query.first()
    except OperationalError:
        db.create_all()
    p = Project(name=name, sample_mask=sample_mask)
    with_transaction(db.session, lambda session: session.add(p))
    return jsonize_model(Project.query.filter_by(id=p.id).one())


class Sample(db.Model):
    __metaclass__ = ResourceMetaClass
    __tablename__ = 'sample'
    __hashidgen__ = HashIds('Sample')

    name = Column(String(80), unique=True)
    # to what project does this sample belong
    _project_id = Column('project_id', Integer, ForeignKey('project.id'))
    # objects forward-related to sample
    sample_stages = relationship(
        'SampleStage', backref='sample', lazy='dynamic')

    @property
    def project_id(self):
        return self.project.obfuscated_id


def get_samples(project_id):
    """
    Returns a JSON array of the samples in a given project.
    """
    p = Project.query.filter_by(id=project_id).first()
    if p is None:
        msg = 'Project {} was not found.'.format(project_id)
        raise NoResultFound(msg)
    return jsonize_models(Sample.query.filter_by(project_id=p.id).all())


def add_sample(project_id, name):
    """
    Adds a new sample.
    """
    p = Project.query.filter_by(obfuscated_id=project_id).first()
    if p is None:
        msg = 'Project "%s" was not found.' % project_id
        raise NoResultFound(msg)
    s = Sample(name=name, project=p)
    with_transaction(db.session, lambda session: session.add(s))
    return jsonize_model(Sample.query.filter_by(id=s.id).one())


class Method(db.Model):
    __metaclass__ = ResourceMetaClass
    __tablename__ = 'method'
    __hashidgen__ = HashIds('Method')

    name = Column(String(80), unique=True)
    description = Column(String(80), unique=False)

    # objects forward-related to method
    sample_stages = relationship(
        'SampleStage', backref='method', lazy='dynamic')


def get_methods():
    """
    Returns a JSON array of methods.
    """
    try:
        methods = Method.query.all()
    except OperationalError:
        return ''
    return jsonize_models(methods)


def add_method(name, description):
    """Adds a new method."""
    try:
        _ = Method.query.first()
    except OperationalError:
        db.create_all()
    m = Method(name=name, description=description)
    with_transaction(db.session, lambda session: session.add(m))
    return jsonize_model(Method.query.filter_by(id=m.id).one())


class SampleStage(db.Model):
    __metaclass__ = ResourceMetaClass
    __tablename__ = 'sample_stage'
    __hashidgen__ = HashIds('SampleStage')

    annotation = Column(Text, unique=False)
    alt_id = Column(Integer, unique=False)
    # relationships
    _sample_id = Column('sample_id', Integer, ForeignKey('sample.id'))
    _method_id = Column('method_id', Integer, ForeignKey('method.id'))
    # objects forward-related to sample stage
    sample_stage_files = relationship(
        'SampleStageFile', backref='sample_stage', lazy='dynamic')

    @property
    def sample_id(self):
        return self.sample.obfuscated_id

    @property
    def method_id(self):
        return self.method.obfuscated_id


def get_stages(sample_id=None, method_id=None):
    """
    Returns stages that are part of sample_id, method_id, or both (boolean AND).
    """
    query = SampleStage.query
    if sample_id is not None:
        query = query.filter_by(sample_id=sample_id)
    if method_id is not None:
        query = query.filter_by(method_id=method_id)
    # check that the db exists
    try:
        stages = query.all()
    except OperationalError:
        return ''
    return '\n'.join([jsonize(s) for s in stages])


def add_stage(sample_id, method_id, annotation, alt_id=None):
    """Adds a new sample stage."""
    try:
        _ = SampleStage.query.first()
    except OperationalError:
        db.create_all()
    s = Sample.query.filter_by(obfuscated_id=sample_id).first()
    if s is None:
        msg = 'Sample ID {} was not found.'.format(sample_id)
        raise NoResultFound(msg)
    m = Method.query.filter_by(obfuscated_id=method_id).first()
    if m is None:
        msg = 'Method ID {} was not found.'.format(method_id)
        raise NoResultFound(msg)
    ss = SampleStage(
        annotation=annotation, sample=s, method=m, alt_id=alt_id)
    with_transaction(db.session, lambda session: session.add(ss))
    return jsonize_model(SampleStage.query.filter_by(id=ss.id).one())


class FileStatus(object):
    complete = 0
    incomplete = 1

class SampleStageFile(db.Model):
    __metaclass__ = ResourceMetaClass
    __tablename__ = 'sample_stage_file'
    __hashidgen__ = HashIds('SampleStageFile')

    file_repr = Column(Text, unique=True)
    relative_file_path = Column(Text, unique=True)
    status = Column(Integer, unique=False)
    # relationships
    _sample_stage_id = Column(
        'sample_stage_id', Integer, ForeignKey('sample_stage.id'))

    @property
    def sample_stage_id(self):
        return self.sample_stage.obfuscated_id

    # create a sample stage file object
    def __init__(self, sample_stage, status=FileStatus.incomplete):
        kwds = {}
        # set the sample stage
        kwds['sample_stage'] = sample_stage
        # construct the filename based on project, sample, and method
        # TODO: There is no file extension...
        method = sample_stage.method
        sample = sample_stage.sample
        project = sample.project
        relpath, counter = create_upload_filename(
            app.config['STORE_PATH'],
            '{project_id:03d}/{sample_id:04d}'.format(
                project_id=project.id, sample_id=sample.id),
            '{method_id:03d}'.format(method_id=method.id))
        kwds['relative_file_path'] = relpath
        kwds['file_repr'] = \
            '{project:}/{sample:}/{method:}-{counter:03d}'.format(
                project=project.name, sample=sample.name,
                method=method.name, counter=counter)
        # set the status of the file transfer
        kwds['status'] = status
        super().__init__(**kwds)
    # representation of sample stage file
    def __repr__(self):
        return '<Sample Stage File {id:}: ' \
               '{file:} ({relpath:}), status={stat:}>'.format(
                    id=self.id, file=self.file_repr,
                    relpath=self.relative_file_path, stat=self.status)


def create_upload_filename(*args, **kwds):
    counter = 0
    prefix = args[0].rstrip('/')
    relpath = '/'.join(s.rstrip('/') for s in args[1:])
    while True:
        try:
            suffix = '{relpath:}-{counter:03d}'.format(
                relpath=relpath, counter=counter)
            trial = '{prefix:}/{suffix:}'.format(
                prefix=prefix, suffix=suffix)
            open(trial).close() # attempt to open the file
            # file opened and was closed successfully, i.e. file exists
            counter += 1
        except IOError:
            # file failed to open, i.e. does not exist
            return (suffix, counter)


def get_files(sample_stage_id=None):
    """
    Returns a newline-separated JSONized files that belong to a sample stage.
    """
    query = SampleStageFile.query
    if sample_stage_id is not None:
        query = query.filter_by(sample_stage_id=sample_stage_id)
    try:
        files = query.all()
    except OperationalError:
        return ''
    return '\n'.join([jsonize(f) for f in files])


def add_file(sample_stage_id):
    """
    Adds a new file to the sample stage.
    """
    try:
        _ = SampleStageFile.query.first()
    except OperationalError:
        db.create_all()
    ss = SampleStage.query.filter_by(id=sample_stage_id).first()
    if ss is None:
        msg = 'SampleStage ID {} was not found.'.format(sample_stage_id)
        raise NoResultFound(msg)
    ssf = SampleStageFile(sample_stage=ss)
    with_transaction(db.session, lambda session: session.add(ssf))
    return jsonize_model(SampleStageFile.query.filter_by(id=ssf.id))

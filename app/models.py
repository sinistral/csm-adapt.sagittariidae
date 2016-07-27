
import hashids
import json
import re

from flask                     import abort
from sqlalchemy                import Boolean, Column, Enum, ForeignKey, PrimaryKeyConstraint, String, Text, Integer
from sqlalchemy                import event
from sqlalchemy.exc            import OperationalError, IntegrityError
from sqlalchemy.orm            import Session
from sqlalchemy.orm            import relationship
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.exc        import NoResultFound, MultipleResultsFound
from urllib                    import quote

import http

from app import app, db


BAD_URI_PAT  = re.compile("%.{2}|\/|_")
COLLAPSE_PAT = re.compile("-{2,}")


@event.listens_for(Session, 'after_flush_postexec')
def inject_obfuscated_id_after_flush_postexec(session, flush_context):
    """
    Tie into the SQLAlchemy `after_flush_postexec` hook to render for the
    resource model instance an obfuscated ID that is based on the DB-allocated
    ID.  The `after_flush` designation refers to the fact that the hook is run
    after synchronizing the Python model with the (speculative) DB commit.
    This makes the DB-allocated IDs (like autoincrement fields) available to
    the Python model for further manipulation before the final commit.

    cf. http://docs.sqlalchemy.org/en/rel_1_0/orm/events.html?highlight=after_flush_postexec
    """
    def is_resource(m):
        return hasattr(m, '__metaclass__') \
            and (getattr(m, '__metaclass__') == ResourceMetaClass)

    def inject_obfuscated_id(m):
        if is_resource(m) and (m.obfuscated_id is None):
            m.obfuscated_id = m.__hashidgen__.encode(m.id)
        return m

    return [inject_obfuscated_id(m)
            for m in session.identity_map.values()]


def with_transaction(session, f):
    """
    Execute `f` in a DB transaction.  If `f` completes successfully, the
    transaction is committed, otherwise an error is raised and the transaction
    is rolled back.

    `f` must accept a single argument: the database session instance.
    """
    try:
        ret = f(session)
        session.commit()
        return ret
    except Exception, e:
        session.rollback()
        raise e


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


def get_resource(q, abort_not_found=True):
    """
    Retrieve a single resource using the model using a Flask-SQLAlchemy query.
    A `MultipleResultsFound` error will be raised if more than one result is
    returned by the query. In most cases it is sufficient to allow this to
    bubble up and be captured as a `500` ServerInternalError as - given a
    rigidly-defined API that doesn't allow the client to specify query
    parameters directly - it is more likely that the query has been incorrectly
    constructed from the request parameters than it is that the user has
    constructed a bad query.
    """
    r = q.one_or_none()
    # Note the use of `one_or_none` and not `first_or_none`; the latter won't
    # complain if multiple resources are returned.  In almost all cases we

    # Retrieve the resource and make sure that we're getting exactly one.
    # Because we're allowing an arbitrary filter, it's possible that a buggy
    # call could result in multiple resources being returned, which is almost
    # always the wrong thing to do when *a* resource is sought.  It's worth
    # being paranoid about this because simply returning the first of many
    # resources could result in mutating changes being applied to the wrong
    # resource.
    #
    # Note, therefore, that we're NOT using Flask-SQLAlchemy's `first_or_404`,
    # which won't complain if multiple results are returned.

    if r is None and abort_not_found:
        abort(http.HTTP_404_NOT_FOUND)
    else:
        return r


class UserAuthentication(db.Model):
    __tablename__ = 'user_authn'

    # What agent is responsible for the authentication of this user?
    authenticator_id = Column(String(256), primary_key=True)
    # The authenticator-specific ID of the user.
    authenticator_uid = Column(String(256), primary_key=True)

    # Ref to our own record for the user to whom this auth record applies.
    user_authz_id = Column(Integer, ForeignKey('user_authz.id'))
    user_authz = relationship(
        'UserAuthorization', back_populates='authn_identities')

    PrimaryKeyConstraint('authenticator_id', 'user_id')


class UserAuthorization(db.Model):
    __tablename__ = 'user_authz'
    __metaclass__ = ResourceMetaClass
    __hashidgen__ = HashIds('UserAuthorization')

    # TECHDEBT: Forgive me, future self.
    #
    # Mike Bayer (zzzeek) has a nice description of an Enum recipe that marries
    # the advantages of keeping the enum values in the database with those of
    # having them defined in code:
    # http://techspot.zzzeek.org/2011/01/14/the-enum-recipe/
    #
    # This is how I should be implementing the user status, but in the name of
    # expedience, I'm going to stop with defining the Enum as Good Enough (tm)
    # for now.  When time permits we should revisit this.
    status = Column(Enum('pending-approval', 'active', 'disabled', 'retired'),
                    nullable=False)

    # Which agenc{y,ies} authenticated this user?
    authn_identities = relationship(
        'UserAuthentication', back_populates='user_authz')

    # FIXME: This is an all-or-nothing approach to authorization, which - as a
    # first pass - is probably good enough for internal ADAPT users.  In
    # future, however, we're probably going to want a more fine-grained
    # authorization model; at the very least we may want to constrain the set
    # of projects available to users, or who is permited to make changes to a
    # project.
    authorized = Column(Boolean(create_constraint=True), nullable=False)


def add_user(uid, authenticator_id):
    user_authz = get_user_authorization(
        uid, authenticator_id, abort_not_found=False)

    # An authentication record for this user already exists.  If the user is
    # also authorized, then just return the record for that user.
    if user_authz is not None:
        return user_authz
    else:
        def make_user(session):
            user_authz = UserAuthorization(
                status='pending-approval', authorized=False)
            user_authn = UserAuthentication(
                authenticator_id=authenticator_id, authenticator_uid=uid)
            user_authz.authn_identities.append(user_authn)
            session.add(user_authz)
            session.add(user_authn)
            return user_authz
        uaz = with_transaction(db.session, make_user)

        # Refresh the persisted object so that the relationship-backed
        # attributes are fully realised.
        db.session.refresh(uaz)

        return uaz


def get_user_authorization(uid, authenticator_id, abort_not_found=True):
    uan_q = UserAuthentication.query.filter_by(
        authenticator_id=authenticator_id, authenticator_uid=uid)
    uan = get_resource(uan_q, abort_not_found)
    if uan is None:
        return None
    else:
        return uan.user_authz


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
    Returns a list of dicts, where each contains summary information about a
    project.
    """
    return Project.query.all()


def get_project(abort_not_found=True, **project_filters):
    """
    Retrieve summary information (as a dict) for a single project. The fields
    by which the project is to be identified must be specified as
    `project_filters`,
    ```
    get_project(id="5QMVv")
    ```
    If `abort_not_found` is `True`, processing will be short-circuited with a
    404 if the project can not be found.
    """
    return get_resource(
        Project.query.filter_by(**project_filters), abort_not_found)


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
    return Project.query.filter_by(id=p.id).one()


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


def get_samples(**project_filters):
    """
    Returns a list of dicts where each represents summary data of a sample.
    """
    p = get_project(**project_filters)
    return Sample.query.filter_by(_project_id=p.id).all()


def get_project_sample(project_filters, sample_filters, abort_not_found=True):
    # Retrieve the project that is supposed to contain the sample, signalling a
    # 404 if it does not exist.  Although our obfuscated sample IDs are in fact
    # globally unique, we don't want to leak that fact into the API, since it
    # isn't something that clients should assume as guaranteed behaviour.
    # Samples are only valid in the context of a project, and the API should
    # reflect that, even if we model it differently.
    p = get_project(**project_filters)
    sample_filters['_project_id'] = p.id
    return get_resource(Sample.query.filter_by(**sample_filters))


def add_sample(project_id, name):
    """
    Adds a new sample.
    """
    p = get_project(obfuscated_id=project_id)
    s = Sample(name=name, project=p)
    with_transaction(db.session, lambda session: session.add(s))
    return Sample.query.filter_by(id=s.id).one()


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
    Returns a list of dicts, where each contains summary information about a
    method.
    """
    try:
        methods = Method.query.all()
    except OperationalError:
        return ''
    return methods


def get_method(abort_not_found=True, **filters):
    return get_resource(Method.query.filter_by(**filters), abort_not_found)


def add_method(name, description):
    """Adds a new method."""
    try:
        _ = Method.query.first()
    except OperationalError:
        db.create_all()
    m = Method(name=name, description=description)
    with_transaction(db.session, lambda session: session.add(m))
    return Method.query.filter_by(id=m.id).one()


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


def _sample_stage_token_hashid():
    return hashids.Hashids(salt='SampleStageToken', min_length=5)


def get_sample_stages(sample_id):
    """
    Returns stages for the designated sample.
    """
    s = get_resource(Sample.query.filter_by(obfuscated_id=sample_id))
    # The order of the stages is significant, since they represent a sequence
    # of events for a sample.  Results should naturally be ordered by the
    # primary key, but it doesn't hurt to make sure.
    stages = SampleStage\
             .query\
             .filter_by(_sample_id=s.id)\
             .order_by(SampleStage.id)\
             .all()
    hashid = _sample_stage_token_hashid()
    if len(stages) == 0:
        token = hashid.encode(0)
    else:
        token = hashid.encode(stages[-1].id)
    return stages, token


def get_sample_stage(sample_id, stage_id):
    """
    Returns a particular stage for a particular sample.
    """
    s = get_resource(Sample.query.filter_by(obfuscated_id=sample_id))
    return get_resource(SampleStage.query.filter_by(_sample_id=s.id))


def add_sample_stage(sample_id, method_id, annotation, token, alt_id=None):
    """
    Adds a new sample stage.  Clients are required to echo the token returned
    by `get_sample_stages()` in order to make requests idempotent and avoid
    adding spurious entries to the DB because of retries, etc.
    """
    s = get_resource(Sample.query.filter_by(obfuscated_id=sample_id))
    m = get_resource(Method.query.filter_by(obfuscated_id=method_id))
    i = _sample_stage_token_hashid().decode(token)[0]

    # Make sure that we have a transaction open.  We need to retrieve the list
    # of stages and insert the new stage in a single transaction for the insert
    # token to be valid.  Without this it is possible for accidental duplicates
    # to be inserted because of race conditions or timeouts.
    db.session.begin(subtransactions=True)

    last_stage = SampleStage\
                 .query\
                 .filter_by(_sample_id=s.id)\
                 .order_by(SampleStage.id.desc()).first()
    if last_stage is None:
        last_stage_id = 0
    else:
        last_stage_id = last_stage.id

    if last_stage_id != i:
        abort(409)
    else:
        ss = SampleStage(annotation=annotation,
                         sample=s,
                         method=m,
                         alt_id=alt_id)
        try:
            with_transaction(db.session, lambda session: session.add(ss))
            db.session.commit()
        except:
            db.session.rollback()
            raise
        return SampleStage.query.filter_by(id=ss.id).one()


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
    Returns a list of dicts where each represents a file that belongs to a
    sample stage.
    """
    query = SampleStageFile.query
    if sample_stage_id is not None:
        query = query.filter_by(sample_stage_id=sample_stage_id)
    try:
        files = query.all()
    except OperationalError:
        return ''
    return files


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
    return SampleStageFile.query.filter_by(id=ssf.id)

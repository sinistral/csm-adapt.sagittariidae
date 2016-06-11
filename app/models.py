from app import app, db
from sqlalchemy import ForeignKey, Column, String, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
import json


def dictify(model):
    """Return a model as a dictionary"""
    return dict(kv for kv in iter(model.__dict__.items())
                if not kv[0].startswith('_'))


class Project(db.Model):
    __tablename__ = 'projects'
    id = Column('project_id', Integer, primary_key=True)
    name = Column(String(80), unique=True)
    sample_mask = Column(String(64), unique=False)
    # objects forward-related to project
    samples = relationship('Sample',
                           backref='project',
                           lazy='dynamic')
    # representation of the project
    def __repr__(self):
        return '<Project {id:}: {name:}>'.format(id=self.id, name=self.name)


def get_projects():
    """
    Returns an array of JSON objects, with each element representing a project.
    """
    try:
        projects = Project.query.all()
    except OperationalError:
        return ''
    return json.dumps([dictify(p) for p in projects])


def add_project(name, sample_mask):
    """Adds a new project."""
    p = Project(name=name, sample_mask=sample_mask)
    try:
        _ = Project.query.first()
    except OperationalError:
        db.create_all()
    except IntegrityError:
        msg = 'A Project named "{}" already exists.'.format(name)
        raise IntegrityError(msg)
    db.session.add(p)
    db.session.commit()
    return p.id


class Sample(db.Model):
    __tablename__ = 'samples'
    id = Column('sample_id', Integer, primary_key=True, autoincrement=True)
    name = Column(String(80), unique=True)
    # to what project does this sample belong
    project_id = Column(Integer, ForeignKey('projects.project_id'))
    # objects forward-related to sample
    sample_stages = relationship('SampleStage',
                                 backref='sample',
                                 lazy='dynamic')
    # representation of the sample
    def __repr__(self):
        return '<Sample {id:}: {name:}, project {project_id:}>'.format(
            id=self.id, name=self.name, project_id=self.project_id)


def get_samples(project_id=None):
    """
    Returns a newline-separated JSON of all samples in a given project.
    """
    try:
        if project_id is None:
            samples = Sample.query.all()
        else:
            samples = Sample.query.filter_by(project_id=project_id).all()
    except OperationalError:
        return ''
    return '\n'.join([jsonize(s) for s in samples])


def add_sample(project_id, name):
    """Adds a new sample."""
    p = Project.query.filter_by(id=project_id).first()
    if p is None:
        msg = 'Project ID {} was not found.'.format(project_id)
        raise NoResultFound(msg)
    s = Sample(name=name, project=p)
    try:
        db.session.add(s)
        db.session.commit()
    except IntegrityError:
        msg = 'A Sample named "{}" already exists.'.format(name)
        raise IntegrityError(msg)
    return s.id


class Method(db.Model):
    __tablename__ = 'methods'
    id = Column('method_id', Integer, primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(80), unique=False)
    # objects forward-related to method
    sample_stages = relationship('SampleStage',
                                 backref='method',
                                 lazy='dynamic')
    # representation of the method
    def __repr__(self):
        return '<Method {id:}: {name:}, {descr:}>'.format(
            id=self.id, name=self.name, descr=self.description)


def get_methods():
    """
    Returns a newline-separated JSON of all methods.
    """
    try:
        methods = Method.query.all()
    except OperationalError:
        return ''
    return '\n'.join([jsonize(m) for m in methods])


def add_method(name, description):
    """Adds a new method."""
    m = Method(name=name, description=description)
    try:
        _ = Method.query.first()
    except OperationalError:
        db.create_all()
    except IntegrityError:
        msg = 'A Method named "{}" already exists.'.format(name)
        raise IntegrityError(msg)
    db.session.add(m)
    db.session.commit()
    return m.id


class SampleStage(db.Model):
    __tablename__ = 'sample_stages'
    id = Column('sample_stage_id', Integer, primary_key=True)
    annotation = Column(Text, unique=False)
    alt_id = Column(Integer, unique=False)
    # relationships
    sample_id = Column(Integer, ForeignKey('samples.sample_id'))
    method_id = Column(Integer, ForeignKey('methods.method_id'))
    # objects forward-related to sample stage
    sample_stage_files = relationship('SampleStageFile',
                                      backref='sample_stage',
                                      lazy='dynamic')
    # representation of the sample stage
    def __repr__(self):
        return '<Sample Stage {id:}: {ann:}, alt={alt:}>'.format(
            id=self.id, ann=self.annotation, alt=self.alt_id)


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
    s = Sample.query.filter_by(id=sample_id).first()
    if s is None:
        msg = 'Sample ID {} was not found.'.format(sample_id)
        raise NoResultFound(msg)
    m = Method.query.filter_by(id=method_id).first()
    if m is None:
        msg = 'Method ID {} was not found.'.format(method_id)
        raise NoResultFound(msg)
    ss = SampleStage(annotation=annotation, sample=s, method=m,
                     alt_id=alt_id)
    db.session.add(ss)
    db.session.commit()
    return ss.id


class FileStatus(object):
    complete = 0
    incomplete = 1

class SampleStageFile(db.Model):
    __tablename__ = 'sample_stage_files'
    id = Column('sample_stage_file_id', Integer, primary_key=True)
    file_repr = Column(Text, unique=True)
    relative_file_path = Column(Text, unique=True)
    status = Column(Integer, unique=False)
    # relationships
    sample_stage_id = Column(Integer,
                             ForeignKey('sample_stages.sample_stage_id'))
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
    db.session.add(ssf)
    db.session.commit()
    return ssf.id

from app import db
from sqlalchemy import ForeignKey, Column, String, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Project(Base, db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True)
    sample_id_mask = Column(String(64), unique=False)
    # objects forward-related to project
    samples = relationship('Sample',
                              backref='project',
                              lazy='dynamic')

class Sample(Base, db.Model):
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project.primary_key'),
                           primary_key=True)
    name = Column(String(80), unique=True)
    # objects forward-related to sample
    sample_stages = relationship('SampleStage',
                                    backref='sample',
                                    lazy='dynamic')

class Method(Base, db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(80), unique=False)
    # objects forward-related to method
    sample_stages = relationship('SampleStage',
                                    backref='method',
                                    lazy='dynamic')

class SampleStage(Base, db.Model):
    id = Column(Integer, primary_key=True)
    sample_id = Column(Integer, ForeignKey('sample.primary_key'),
                          primary_key=True)
    method_id = Column(Integer, ForeignKey('method.primary_key'),
                          primary_key=True)
    annotation = Column(Text, unique=False)
    alt_id = Column(Integer, unique=False)
    # objects forward-related to sample stage
    sample_stage_files = relationship('SampleStageFile',
                                         backref='sampleStage',
                                         lazy='dynamic')

class SampleStageFile(Base, db.Model):
    id = Column(Integer, primary_key=True)
    sample_stage_id = Column(Integer,
                                ForeignKey('sampleStage.primary_key'),
                                primary_key=True)
    relative_file_path = Column(Text, unique=True)
    status = Column(Integer, unique=False)

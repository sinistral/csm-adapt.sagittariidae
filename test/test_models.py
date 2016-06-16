
import os
import pytest
import tempfile

from sqlalchemy import Column, Integer

import app
import app.models as models

from app.models import db
from fixtures   import ws
from utils      import decode_json_string


def test_dictify():
    p = models.Project(id=1, obfuscated_id='5QMVv', name='project', sample_mask='###')
    assert {'id'          : '5QMVv-project',
            'name'        : 'project',
            'sample-mask' : '###'} \
        == models.dictify(p)


def test_dictify_no_name():
    class NoName(db.Model):
        __metaclass__ = models.ResourceMetaClass
        __tablename__ = 'no-name'
    assert {'id':'5QMVv'} \
        == models.dictify(NoName(id=1, obfuscated_id='5QMVv'))


def test_uri_name():
    spec = {'foobar'    : 'foobar',
            'fooBar'    : 'foobar',
            'foo bar'   : 'foo-bar',
            'f o o'     : 'f-o-o',
            'foo   bar' : 'foo-bar',
            'foo ~ bar' : 'foo-bar'}
    for kv in iter(spec.items()):
        assert kv[1] == models.uri_name(kv[0])


def test_add_project(ws):
    assert {'id'          : 'PqrX9-manhattan',
            'name'        : 'Manhattan',
            'sample-mask' : 'man-###'} \
        == decode_json_string(
            models.add_project('Manhattan', 'man-###'))


def test_add_method(ws):
    assert {'id'          : 'XZOQ0-x-ray-tomography',
            'name'        : 'X-ray tomography',
            'description' : 'Placeholder description.'} \
        == decode_json_string(
            models.add_method(name='X-ray tomography',
                              description='Placeholder description.'))


def test_add_sample(ws):
    models.add_project(name='Manhattan', sample_mask='man-###')
    assert {'id'   : 'OQn6Q-sample-1',
            'name' : 'sample 1'} \
        == decode_json_string(
            models.add_sample(project_id='PqrX9', name='sample 1'))
    assert 1 == \
        models.db.engine.execute(
            'select project_id from sample where id=1').fetchone()[0]


def test_add_sample_stage(ws):
    models.add_project(name='Manhattan', sample_mask='man-###')
    models.add_sample(project_id='PqrX9', name='sample 1')
    models.add_method(name='X-ray tomography', description='Placeholder description.')
    assert {'id'         : 'Drn1Q',
            'annotation' : 'Annotation',
            'alt-id'     : None} \
        == decode_json_string(
            models.add_stage(sample_id='OQn6Q',
                             method_id='XZOQ0',
                             annotation='Annotation'))
    assert 1 == \
        models.db.engine.execute(
            'select sample_id from sample_stage where id=1').fetchone()[0]
    assert 1 == \
        models.db.engine.execute(
            'select method_id from sample_stage where id=1').fetchone()[0]


from StringIO import StringIO
import json
import os
import pytest
import tempfile

import app
from app import models


@pytest.fixture(scope='function')
def ws(request):
    flask_app = app.app.app
    # Yuck!  Reeeally have to fix the app name!

    fd, fn = tempfile.mkstemp()
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + fn
    flask_app.config['TESTING'] = True
    inst = flask_app.test_client()
    with flask_app.app_context():
        # db initialization goes here
        pass

    def fin():
        os.close(fd)
        os.unlink(fn)
    request.addfinalizer(fin)
    return inst


def decode_json_string(s):
    return json.load(StringIO(s))


def test_0(ws):
    rsp = ws.get('/')
    assert rsp.data == b'Hello, world!'


def test_0_projects(ws):
    rsp = ws.get('/projects')
    assert rsp.data is ''


def test_1_projects(ws):
    name = 'project3'
    mask = '###'
    models.add_project(name, mask)
    rsp = decode_json_string(ws.get('/projects').data)
    assert len(rsp) == 1
    assert rsp[0] == {'id': 1, 'name': name, 'sample_mask': mask}

def test_1_methods(ws):
    name = 'method0'
    desc = 'placeholder description'
    models.add_method(name, desc)
    rsp = decode_json_string(ws.get('/methods').data)
    assert len(rsp) == 1
    assert rsp[0] == {'id':1, 'name':name, 'description':desc}

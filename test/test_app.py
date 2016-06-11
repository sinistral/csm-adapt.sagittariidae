
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
    models.add_project('project3', '###')
    rsp = decode_json_string(ws.get('/projects').data)
    assert len(rsp) == 1
    assert rsp[0] == {'id': 1, 'name': 'project3', 'sample_mask': '###'}


import os
import pytest
import tempfile

import app

from app      import models
from fixtures import ws
from utils    import decode_json_string


def test_0(ws):
    rsp = ws.get('/')
    assert rsp.data == b'Hello, world!'


def test_0_projects(ws):
    rsp = ws.get('/projects')
    assert '[]' == rsp.data


def test_1_projects(ws):
    name = 'Project 3'
    mask = '###'
    models.add_project(name, mask)
    rsp = decode_json_string(ws.get('/projects').data)
    assert len(rsp) == 1
    assert {'id':'PqrX9-project-3', 'name': name, 'sample-mask': mask} == rsp[0]

def test_1_methods(ws):
    name = 'Method 1'
    desc = 'Placeholder description.'
    models.add_method(name, desc)
    rsp = decode_json_string(ws.get('/methods').data)
    assert len(rsp) == 1
    assert {'id':'XZOQ0-method-1', 'name':name, 'description':desc} == rsp[0]

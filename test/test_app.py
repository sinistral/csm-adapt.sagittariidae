
import os
import pytest
import tempfile

import app

from app      import models
from fixtures import sample, ws
from utils    import decode_json_string


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
    assert [{'id':'XZOQ0-method-1', 'name':name, 'description':desc}] \
        == rsp

def test_get_sample_with_context(ws, sample):
    rsp = decode_json_string(ws.get('/projects/PqrX9-project-0/samples').data)
    assert [{'id'   : 'OQn6Q-sample-1',
             'name' : 'sample 1'}] \
        == rsp


def test_get_sample_without_context(ws, sample):
    rsp = decode_json_string(ws.get('/projects/PqrX9/samples').data)
    assert [{'id'   : 'OQn6Q-sample-1',
             'name' : 'sample 1'}] \
        == rsp


def test_sample_project_not_found(ws, sample):
    rsp = ws.get('/projects/00000-project-X/samples')
    assert rsp.status_code == 404

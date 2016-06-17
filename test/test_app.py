
import os
import pytest
import tempfile

from app      import models
from fixtures import sample, sample_with_stages, ws
from utils    import decode_json_string


def test_no_projects(ws):
    rsp = ws.get('/projects')
    assert [] == decode_json_string(rsp.data)


def test_1_projects(ws, sample):
    rsp = decode_json_string(ws.get('/projects').data)
    assert [{'id':'PqrX9-manhattan',
             'name': 'Manhattan',
             'sample-mask': 'man-###'}] \
        == rsp


def test_get_project_with_context(ws, sample):
    rsp = decode_json_string(ws.get('/projects/PqrX9-manhattan').data)
    assert {'id':'PqrX9-manhattan',
             'name': 'Manhattan',
             'sample-mask': 'man-###'} \
        == rsp


def test_get_project_without_context(ws, sample):
    rsp = decode_json_string(ws.get('/projects/PqrX9').data)
    assert {'id':'PqrX9-manhattan',
             'name': 'Manhattan',
             'sample-mask': 'man-###'} \
        == rsp


def test_get_methods(ws):
    name = 'Method 1'
    desc = 'Placeholder description.'
    models.add_method(name, desc)
    rsp = decode_json_string(ws.get('/methods').data)
    assert [{'id':'XZOQ0-method-1', 'name':name, 'description':desc}] \
        == rsp


def test_get_sample_with_context(ws, sample):
    rsp = decode_json_string(ws.get('/projects/PqrX9-project-0/samples').data)
    assert [{'id'      : 'OQn6Q-sample-1',
             'name'    : 'sample 1',
             'project' : 'PqrX9-manhattan'}] \
        == rsp


def test_get_sample_without_context(ws, sample):
    rsp = decode_json_string(ws.get('/projects/PqrX9/samples').data)
    assert [{'id'      : 'OQn6Q-sample-1',
             'name'    : 'sample 1',
             'project' : 'PqrX9-manhattan'}] \
        == rsp


def test_sample_project_not_found(ws, sample):
    rsp = ws.get('/projects/00000-project-X/samples')
    assert rsp.status_code == 404


def test_sample_not_found(ws, sample):
    rsp = ws.get('projects/5QMVv/samples/invalid-sample')
    assert rsp.status_code == 404


def test_get_sample(ws, sample_with_stages):
    rsp = decode_json_string(ws.get('/projects/PqrX9/samples/OQn6Q').data)
    assert \
        {'id'      : 'OQn6Q-sample-1',
         'name'    : 'sample 1',
         'project' : 'PqrX9-manhattan'} \
        == rsp


def test_get_stages(ws, sample_with_stages):
    rsp = decode_json_string(ws.get('/projects/PqrX9/samples/OQn6Q/stages').data)
    assert [{'id'         : 'Drn1Q-1',
             'method'     : 'XZOQ0-x-ray-tomography',
             'sample'     : 'OQn6Q-sample-1',
             'alt-id'     : None,
             'annotation' : 'Annotation 0'},
            {'id'         : 'bQ8bm-2',
             'method'     : 'XZOQ0-x-ray-tomography',
             'sample'     : 'OQn6Q-sample-1',
             'alt-id'     : None,
             'annotation' : 'Annotation 1'}] \
        == rsp


import os
import pytest
import tempfile

import app.models as models

from fixtures   import ws


def test_add_project(ws):
    m = models.add_project('Manhattan', 'man-###')
    assert 1 == m.id
    assert 'PqrX9' == m.obfuscated_id
    assert 'Manhattan' == m.name
    assert 'man-###' == m.sample_mask


def test_add_method(ws):
    m = models.add_method(name='X-ray tomography',
                          description='Placeholder description.')
    assert 1 == m.id
    assert 'XZOQ0' == m.obfuscated_id
    assert 'X-ray tomography' == m.name
    assert 'Placeholder description.' == m.description


def test_add_sample(ws):
    models.add_project(name='Manhattan', sample_mask='man-###')
    m = models.add_sample(project_id='PqrX9', name='sample 1')
    assert 1 == m.id
    assert 'OQn6Q' == m.obfuscated_id
    assert 'sample 1' == m.name
    assert 1 == m._project_id
    assert 'PqrX9' == m.project_id


def test_add_sample_stage(ws):
    models.add_project(name='Manhattan', sample_mask='man-###')
    models.add_sample(project_id='PqrX9', name='sample 1')
    models.add_method(name='X-ray tomography', description='Placeholder description.')
    m = models.add_stage(
        sample_id='OQn6Q', method_id='XZOQ0', annotation='Annotation')
    assert 1 == m.id
    assert 'Drn1Q' == m.obfuscated_id
    assert None == m.alt_id
    assert 'Annotation' == m.annotation
    assert 1 == m._sample_id
    assert 'OQn6Q' == m.sample_id
    assert 1 == m._method_id
    assert 'XZOQ0' == m.method_id

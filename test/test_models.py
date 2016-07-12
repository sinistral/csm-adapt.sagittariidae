
import os
import pytest
import werkzeug

import app.models as models

from fixtures import sample, sample_with_stages, ws


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
    t = models._sample_stage_token_hashid().encode(0)
    m = models.add_sample_stage(
        sample_id='OQn6Q', method_id='XZOQ0', token=t, annotation='Annotation')
    assert 1 == m.id
    assert 'Drn1Q' == m.obfuscated_id
    assert None == m.alt_id
    assert 'Annotation' == m.annotation
    assert 1 == m._sample_id
    assert 'OQn6Q' == m.sample_id
    assert 1 == m._method_id
    assert 'XZOQ0' == m.method_id


def test_get_no_sample_stages(sample):
    s = sample['sample']
    (stages, token) = models.get_sample_stages(s.obfuscated_id)
    assert 0 == len(stages)
    assert models._sample_stage_token_hashid().encode(0) == token


def test_add_new_stage(sample_with_stages):
    s = sample_with_stages['sample']
    m = sample_with_stages['method']
    h = models._sample_stage_token_hashid()

    # Pre-validate that we have the expected number of stages to start with.
    (stages, token) = models.get_sample_stages(s.obfuscated_id)
    assert 2 == len(stages)
    assert h.encode(2) == token

    # Now add the new stage, using the correct ID.
    models.add_sample_stage(s.obfuscated_id, m.obfuscated_id, None, token)

    # Validate that the record has been added to the DB.
    (stages, token) = models.get_sample_stages(s.obfuscated_id)
    assert 2+1 == len(stages)
    assert h.encode(2+1) == token


def test_add_stage_too_far_ahead(sample_with_stages):
    s = sample_with_stages['sample']
    m = sample_with_stages['method']
    h = models._sample_stage_token_hashid()

    # Pre-validate that we have the expected number of stages to start with.
    (stages, token) = models.get_sample_stages(s.obfuscated_id)
    assert 2 == len(stages)
    assert h.encode(2) == token

    # Now add the new stage, using the existing ID and incorrect token
    t = h.encode(999)
    with pytest.raises(werkzeug.exceptions.Conflict) as conflict:
        models.add_sample_stage(s.obfuscated_id, m.obfuscated_id, None, t)

    # Validate that NO record has been added to the DB.
    (stages, token) = models.get_sample_stages(s.obfuscated_id)
    assert 2 == len(stages)
    assert h.encode(2) == token


def test_add_user(ws):
    u = models.add_user('123', 'foo.com')
    assert u is not None
    assert 1 == u.id
    assert 1 == len(u.authn_identities)
    u = models.get_user_authorization('123', 'foo.com')
    assert u is not None
    assert 1 == u.id
    assert 1 == len(u.authn_identities)

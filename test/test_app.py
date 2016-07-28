
import json

from app      import models, http
from fixtures import *
from utils    import decode_json_string


def putreq(ws, url, data):
    data.update({'auth-token': 'f00'})
    return ws.put(url, data=json.dumps(data), content_type='application/json')

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
    assert http.HTTP_404_NOT_FOUND == rsp.status_code


def test_sample_not_found(ws, sample):
    rsp = ws.get('projects/5QMVv/samples/invalid-sample')
    assert http.HTTP_404_NOT_FOUND == rsp.status_code


def test_add_sample_stage(ws, user, sample):
    token = models._sample_stage_token_hashid().encode(0)
    rsp = putreq(ws,
                 '/projects/PqrX9/samples/OQn6Q/stages/' + token,
                 {'method': 'XZOQ0', 'annotation': 'Stage annation'})
    assert http.HTTP_201_CREATED == rsp.status_code
    assert {'id'        : 'Drn1Q-1',
            'sample'    : 'OQn6Q-sample-1',
            'alt-id'    : None,
            'method'    : 'XZOQ0-x-ray-tomography',
            'annotation': 'Stage annation'} \
            == decode_json_string(rsp.data)


def test_add_sample_stage_unauthorized_user(ws, flask_app, user, sample):
    flask_app.config['JWT_DECODER']=lambda x: {'uid': 'anonymous',
                                               'authenticator': 'anonymizer'}
    rsp = putreq(ws, '/projects/PqrX9/samples/OQn6Q/stages/f00',{})
    assert http.HTTP_403_FORBIDDEN == rsp.status_code


def test_get_sample(ws, sample_with_stages):
    rsp = decode_json_string(ws.get('/projects/PqrX9/samples/OQn6Q').data)
    assert {'id'      : 'OQn6Q-sample-1',
            'name'    : 'sample 1',
            'project' : 'PqrX9-manhattan'} \
            == rsp


def test_get_stages(ws, sample_with_stages):
    rsp = decode_json_string(ws.get('/projects/PqrX9/samples/OQn6Q/stages').data)
    assert {'token'   : 'kyDbw',
            'stages'  : [{'id'         : 'Drn1Q-1',
                          'method'     : 'XZOQ0-x-ray-tomography',
                          'sample'     : 'OQn6Q-sample-1',
                          'alt-id'     : None,
                          'annotation' : 'Annotation 0'},
                         {'id'         : 'bQ8bm-2',
                          'method'     : 'XZOQ0-x-ray-tomography',
                          'sample'     : 'OQn6Q-sample-1',
                          'alt-id'     : None,
                          'annotation' : 'Annotation 1'}]} \
        == rsp


def test_get_method(ws, sample_with_stages):
    rsp = decode_json_string(ws.get('/methods/XZOQ0-x-ray-tomography').data)
    assert {'id'          : 'XZOQ0-x-ray-tomography',
            'name'        : 'X-ray tomography',
            'description' : 'Placeholder description.'} \
            == rsp


def test_method_not_found(ws, sample_with_stages):
    rsp = ws.get('/methods/invalid-method')
    assert 404 == rsp.status_code


def test_add_user_unauthenticated(ws):
    rsp = ws.put('/users/add?uid=123&authenticator=google.com')
    assert 401 == rsp.status_code


def test_add_user_authenticated_not_present(flask_app, ws):
    rsp = ws.put('/users/add?uid=123&authenticator=google.com',
                 data=json.dumps({'auth-token': 'f00'}),
                 content_type='application/json')
    assert 202 == rsp.status_code


def test_get_user_pending(flask_app, ws):
    rsp = ws.put('/users/add?uid=123&authenticator=google.com',
                 data=json.dumps({'auth-token': 'f00'}),
                 content_type='application/json')
    assert 202 == rsp.status_code
    u = decode_json_string(ws.get('/users/google.com/123',
                                  data=json.dumps({'auth-token': 'f00'}),
                                  content_type='application/json').data)
    assert 'Lvg7v' == u['id']
    authn_ident = u['authentication-identities']
    assert 1 == len(authn_ident)
    assert 'google.com' == authn_ident[0]['authenticator-id']
    assert '123' == authn_ident[0]['authenticator-uid']

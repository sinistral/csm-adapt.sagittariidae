
import flask
import json
import pytest

from sqlalchemy          import Column, Integer
from werkzeug.exceptions import Unauthorized

import app

from app.models import Method, Project, Sample, SampleStage
from app.models import db
from app.views  import authenticated, jsonize
from utils      import decode_json_string

from fixtures   import json_encoder


def reqctx(dat):
    test_app = flask.Flask(__name__)
    hdr = {'Content-Type': 'application/json'}
    if dat is None:
        json_data = json.dumps({})
    else:
        json_data = json.dumps(dat)
    return test_app.test_request_context(
        '/uri',
        method='GET',
        data=json_data,
        headers=hdr)


def test_authenticated_decorator():
    @authenticated
    def testfn(auth_token=None):
        pass
    with reqctx({'auth-token': 'XXX'}):
        testfn()


def test_authenticated_decorator_no_token():
    @authenticated
    def testfn():
        pass
    with reqctx(None):
        with pytest.raises(Unauthorized):
            testfn()


def test_dictify(json_encoder):
    p = Project(id=1, obfuscated_id='5QMVv', name='project', sample_mask='###')
    assert {'id'            : 1,
            'obfuscated-id' : '5QMVv',
            'name'          : 'project',
            'sample-mask'   : '###'} \
            == json_encoder._dictify(p)


def test_dictify_exclusions(json_encoder):
    p = Project(id=1, obfuscated_id='5QMVv', name='project', sample_mask='###')
    assert {'obfuscated-id' : '5QMVv',
            'sample-mask'   : '###'} \
            == json_encoder._dictify(p, {'id', 'name'})


def test_uri_name(json_encoder):
    spec = {'foobar'    : 'foobar',
            'fooBar'    : 'foobar',
            'foo bar'   : 'foo-bar',
            'f o o'     : 'f-o-o',
            'foo   bar' : 'foo-bar',
            'foo ~ bar' : 'foo-bar'}
    for kv in iter(spec.items()):
        assert kv[1] == json_encoder._uri_name('FoOby', kv[0]).split('-', 1)[1]

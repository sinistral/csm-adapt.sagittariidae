
import os
import pytest
import tempfile

import app
import app.models as models
import app.views as views


TEST_USER='test-user'
TEST_AUTHENTICATOR='test-authenticator'

@pytest.fixture(scope='function')
def flask_app(request):
    fa = app.app.app
    # Yuck!  Reeeally have to fix the app name!

    fd, fn = tempfile.mkstemp()
    fa.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + fn
    fa.config['TESTING'] = True

    token = {'uid':           TEST_USER,
             'authenticator': TEST_AUTHENTICATOR}
    fa.config['JWT_DECODER']=lambda x: token

    with fa.app_context():
        models.db.create_all()
        pass

    def fin():
        os.close(fd)
        os.unlink(fn)
    request.addfinalizer(fin)

    return fa


@pytest.fixture(scope='function')
def ws(flask_app):
    return flask_app.test_client()


@pytest.fixture(scope='function')
def user():
    uid = models.add_user(TEST_USER, TEST_AUTHENTICATOR).obfuscated_id
    models._approve_user(uid)


@pytest.fixture(scope='function')
def sample(ws):
    project = models.add_project(name='Manhattan', sample_mask='man-###')
    sample = models.add_sample(project_id='PqrX9', name='sample 1')
    method = models.add_method(name='X-ray tomography', description='Placeholder description.')
    return {'app'     : ws,
            'project' : project,
            'sample'  : sample,
            'method'  : method}


@pytest.fixture(scope='module')
def json_encoder(request):
    return views.DBModelJSONEncoder()


@pytest.fixture(scope='function')
def sample_with_stages(sample):
    hashid = models._sample_stage_token_hashid()
    token1 = hashid.encode(0)
    stage1 = models.add_sample_stage(sample_id=sample['sample'].obfuscated_id,
                                     method_id=sample['method'].obfuscated_id,
                                     annotation='Annotation 0',
                                     token=token1)
    token2 = hashid.encode(1)
    stage2 = models.add_sample_stage(sample_id=sample['sample'].obfuscated_id,
                                     method_id=sample['method'].obfuscated_id,
                                     annotation='Annotation 1',
                                     token=token2)
    sample.update({'stages': [stage1, stage2]})
    return sample

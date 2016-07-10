
import os
import pytest
import tempfile

import app
import app.models as models
import app.views as views


@pytest.fixture(scope='function')
def ws(request):
    flask_app = app.app.app
    # Yuck!  Reeeally have to fix the app name!

    fd, fn = tempfile.mkstemp()
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + fn
    flask_app.config['TESTING'] = True
    inst = flask_app.test_client()
    with flask_app.app_context():
        app.models.db.create_all()
        pass

    def fin():
        os.close(fd)
        os.unlink(fn)
    request.addfinalizer(fin)
    return inst


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
    sample.update({'method' : models.add_method('Smoke test', 'Placeholder'),
                   'stages' : [models.add_stage(sample_id='OQn6Q',
                                                method_id='XZOQ0',
                                                annotation='Annotation 0'),
                               models.add_stage(sample_id='OQn6Q',
                                                method_id='XZOQ0',
                                                annotation='Annotation 1')]})
    return sample

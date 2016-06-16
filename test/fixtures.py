
import os
import pytest
import tempfile

import app

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

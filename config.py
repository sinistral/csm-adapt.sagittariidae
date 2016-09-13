
import os


TESTING = os.environ.get('FLASK_TESTING') is not None

WTF_CSRF_ENABLED = True
SECRET_KEY = ']`<{e&b$D5)tzd)>242KyFGz8jEZzk8:'

THREADS_PER_PAGE = 8

# The location from which we'll serve the static site pages and *Script source
# files.
STATIC_ROOT = 'static'
# The permanent home for uploaded data files, and the directory from which they
# will be served.
STORE_PATH  = '/mnt/adapt'
# Location in which uploaded files are staged until verified and moved into
# their permanent home.
UPLOAD_PATH = os.path.join(STORE_PATH, '.upload')

# The maximum size of a request message.  This is constrained to prevent us
# from being swamped by clients trying to upload large files in one request.
MAX_CONTENT_LENGTH = (1 * 1024 * 1024) + (512 * 1024)

BASEDIR = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:////var/db/sagittariidae/sagittariidae.db'
SQLALCHEMY_MIGRATE_REPO = '/var/db/sagittariidae/db_repository'

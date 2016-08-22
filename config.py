
import os

WTF_CSRF_ENABLED = True
SECRET_KEY = ']`<{e&b$D5)tzd)>242KyFGz8jEZzk8:'

THREADS_PER_PAGE = 8

STORE_PATH = '/mnt/adapt'
UPLOAD_PATH = os.path.join(STORE_PATH, '.upload')

MAX_CONTENT_LENGTH = (1 * 1024 * 1024) + (512 * 1024)

basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'db/app.db')
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db/db_repository')

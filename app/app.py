
import logging
import time

from flask            import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config.from_object('config')

# Please use a sane timezone for log entries so that we don't have to jump
# through daylight savings hoops.
logging.Formatter.converter = time.gmtime
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(module)s,l%(lineno)d : %(message)s')

logger = app.logger

if app.config['DEBUG'] == True:
    # Log to the console when in debug/test mode
    cons_log = logging.StreamHandler()
    cons_log.setLevel(logging.DEBUG)
    cons_log.setFormatter(formatter)
    logger.addHandler(cons_log)
    # Also log to a local file, rather than to the system log dir
    log_file = 'sagittariidae.log'
else:
    # When in production, log to a file in the system log dir.
    # TODO: Add a `logrotate` cron job to manage the log file.
    log_file = '/var/log/sagittariidae.log'

file_log = logging.FileHandler(log_file)
file_log.setFormatter(formatter)
file_log.setLevel(logging.DEBUG)

logger.addHandler(file_log)
logging.getLogger('werkzeug').addHandler(file_log)
logging.getLogger('sqlalchemy').addHandler(file_log)

logger.info('Sagittariidae startup')

# Init the DB and load our models so that they can be processed by SQLAlchemy.
db = SQLAlchemy(app)

import models, views

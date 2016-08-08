
import logging
import time

from flask            import Flask
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
db = SQLAlchemy(app)

app.config.from_object('config')

# Please use a sane timezone for log entries so that we don't have to jump
# through daylight savings hoops.
logging.Formatter.converter = time.gmtime
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(threadName)s,%(module)s,l%(lineno)d : %(message)s')

# Set up the level at which we want to log
if app.config['TESTING'] or app.config['DEBUG']:
    level = logging.DEBUG
else:
    level = logging.INFO

loggers = {app.logger                      : None,
           logging.getLogger('werkzeug')   : logging.INFO,
           logging.getLogger('sqlalchemy') : logging.WARN}
handlers = []

# Set up the log handlers.
if app.config['TESTING'] or app.config['DEBUG']:
    log_file = 'sagittariidae.log'
    cons_log = logging.StreamHandler()
    handlers.append(cons_log)
else:
    # When in production, log to a file in the system log dir.
    # TODO: Add a `logrotate` cron job to manage the log file.
    log_file = '/var/log/sagittariidae.log'

file_log = logging.FileHandler(log_file)
handlers.append(file_log)

# Assign handlers to loggers and set them all at the appropriate level
for handler in handlers:
    handler.setLevel(level)
    handler.setFormatter(formatter)
    for logger in loggers:
        logger.setLevel(loggers[logger] or level)
        logger.addHandler(handler)

try:
    logger.info('Sagittariidae is starting ...')

    # Load "leaf" modules.  These may depend only on `app.app` which has now
    # been initialised
    import models

    # Lead "middleware" modules.  These may depend on both leaf modules and on
    # `app.app`.
    import views

    # And we're done
    logger.info('Sagittariidae is ready to serve.')
except Exception, e:
    logger.error('Startup error', exc_info=e)
    import sys
    sys.exit(1)

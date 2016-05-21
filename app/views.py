from app import app
from flask import render_template

@app.route('/')
@app.route('/index')
def index():
    ifile = 'layout/index.html'
    try:
        open(ifile).close()
    except IOError:
        msg = '{} not found'.format(ifile)
        return msg
    with open(ifile) as ifs:
        return ifs.read()

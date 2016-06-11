from app import app, models
# from flask import render_template


@app.route('/')
def root():
    return 'Hello, world!'


@app.route('/projects')
def projects():
    return models.get_projects()


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
    # return render_template(ifile)


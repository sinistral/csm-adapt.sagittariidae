
from flask import jsonify, request
from app import app, models
from exceptions import NotFound

# ------------------------------------------------------------ api routes --- #

@app.route('/projects', methods=['GET'])
def get_projects():
    return models.get_projects()


@app.route('/projects/<project>/samples', methods=['GET'])
def get_project_samples(project):
    return models.get_samples(project.split('-')[0])


@app.route('/methods', methods=['GET'])
def get_methods():
    return models.get_methods()

# --------------------------------------------------------- static routes --- #

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

# --------------------------------------------- errors and error handlers --- #

@app.errorhandler(NotFound)
def handle_resource_not_found(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

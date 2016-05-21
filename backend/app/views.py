from app import app
from flask import render_template
from flask import Blueprint

bp = Blueprint('pages', __name__, template_folder='/pages')
app.register_blueprint(bp)

@bp.route('/')
@bp.route('/index')
def index():
    ifile = 'pages/index.html'
    try:
        open(ifile).close()
    except IOError:
        msg = '{} not found'.format(ifile)
        return msg
    return render_template(ifile)

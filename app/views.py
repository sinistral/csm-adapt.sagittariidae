
from flask import jsonify, request
from app import app, db, models

import json
import re

from urllib import quote

# ------------------------------------------------------------ api routes --- #

@app.route('/projects', methods=['GET'])
def get_projects():
    return jsonize(models.get_projects())


@app.route('/projects/<project>', methods=['GET'])
def get_project(project):
    return jsonize(models.get_project(obfuscated_id=project.split('-')[0]))


@app.route('/projects/<project>/samples', methods=['GET'])
def get_project_samples(project):
    return jsonize(models.get_samples(obfuscated_id=project.split('-')[0]))


@app.route('/methods', methods=['GET'])
def get_methods():
    return jsonize(models.get_methods())

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

# -------------------------------------------------- custom JSON encoding --- #

class DBModelJSONEncoder(json.JSONEncoder):

    BAD_URI_PAT  = re.compile("%.{2}|\/|_")
    COLLAPSE_PAT = re.compile("-{2,}")

    def _uri_name(self, name):
        """
        Convert the name of a resource (like a project or sample) into a
        URI-friendly form.  This function has strong opinions about what a
        "good" URI ID is, and will complain if the ID cannot be rendered in
        an acceptable form.  In particular, it should not contain any
        characters that need to be escaped; cf. `urllib.quote()`.
        """
        # URI-escape special characters
        new_name = quote(name.lower().replace(" ", "-"))
        # Convert escapes into underscores; i.e. foo%20bar -> foo-bar
        new_name = re.sub(self.BAD_URI_PAT, '-', new_name)
        # Collapse multiple consecutive hyphens; i.e. foo---bar -> foo-bar
        new_name = re.sub(self.COLLAPSE_PAT, '-', new_name)
        # And return our pretty new identifier
        return new_name

    def _dictify(self, model, exclude={}):
        """
        Return a model as a dictionary. 'Private' attributes are removed and
        underscores are replaced with more hyphens in attribute names, making
        for more aesthetically pleasing HTTP data maps.
        """
        assert hasattr(model, 'id')
        assert model.id is not None, 'Model\'s ID may not be None'
        assert hasattr(model, 'obfuscated_id')
        assert model.obfuscated_id is not None, 'Model\'s obfuscated ID may not be None'

        def tr(kv):
            return (kv[0].replace('_', '-'), kv[1])
        return dict(tr(kv) for kv in iter(model.__dict__.items())
                    if (not (kv[0].startswith('_') or (kv[0] in exclude))))

    def strip_private_fields(self, d):
        del d['obfuscated-id']
        return d

    def _encodeProject(self, p):
        d = self._dictify(p)
        d['id'] = '-'.join([d['obfuscated-id'], self._uri_name(d['name'])])
        return self.strip_private_fields(d)

    def _encodeSample(self, s):
        d = self._dictify(s, {'project'})
        d['project'] = '-'.join(
            [s.project.obfuscated_id, self._uri_name(s.project.name)])
        d['id'] = '-'.join([d['obfuscated-id'], self._uri_name(d['name'])])
        return self.strip_private_fields(d)

    def _encodeMethod(self, m):
        d = self._dictify(m)
        d['id'] = '-'.join([d['obfuscated-id'], self._uri_name(d['name'])])
        return self.strip_private_fields(d)

    def _encodeModel(self, m):
        return self.strip_private_fields(self._dictify(m))

    def default(self, thing):
        f = {models.Project : self._encodeProject,
             models.Sample  : self._encodeSample,
             models.Method  : self._encodeMethod,
             db.Model       : self._encodeModel
        }.get(thing.__class__, lambda x: json.JSONEncoder.default(self, x))
        return f(thing)


def jsonize(x):
    return json.dumps(x, cls=DBModelJSONEncoder)

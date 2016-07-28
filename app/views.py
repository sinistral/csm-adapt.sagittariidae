
import json
import re

from flask import abort, jsonify, request
from urllib import quote

import http
import authz

from app import app, db, models

# ------------------------------------------------------------ api routes --- #

def authenticated(f):
    """
    A decorator for functions that may only be used by an authenticated user.
    Decorated functions must accept the keyword argument `auth_token`, which
    will the decorator will inject into the arguments provided by the caller if
    the token is successfuly verified, e.g.

    ```
    @authenticated
    def noop(auth_token=None):
        pass

    @authenticated
    def echo(x, auth_token=None):
        return x
    ```

    If the token can not be verified, an error will be raised and the decorated
    function will not be called.
    """
    def authenticated_fn(*args, **kwargs):
        # API calls that should contain an auth token but don't are an error
        # the part of the client.
        authd = request.json is not None \
                and request.json.has_key('auth-token') \
                and request.json['auth-token'] is not None

        if not authd:
            abort(http.HTTP_401_UNAUTHORIZED)
        else:
            auth_token = request.json['auth-token']
            # We depend on the decoder to raise an error if the token is
            # invalid.  The operations being performed must validate
            # independently that the (now authenticated) user is authorized.
            kwargs['auth_token'] = app.config['JWT_DECODER'](auth_token)
            return f(*args, **kwargs)

    # Flask protects its users from themselves by ensuring that the same
    # function isn't mapped to multiple route endpoints.  It does this by
    # function name.  Decorated functions will all look the same to Flask
    # unless we hack the name.
    authenticated_fn.__name__ = '_'.join(['authenticated', f.__name__])
    return authenticated_fn


@app.route('/projects', methods=['GET'])
def get_projects():
    return jsonize(models.get_projects())


@app.route('/projects/<project>', methods=['GET'])
def get_project(project):
    return jsonize(models.get_project(obfuscated_id=as_id(project)))


@app.route('/projects/<project>/samples', methods=['GET'])
def get_project_samples(project):
    # Allow clients to search for a sample rather than having to retrieve all
    # of the samples for a project (even if the latter is arguably the more
    # RESTful approach).  This enables a URL of the form:
    #
    #   http://.../projects/qwErt/samples?name=P001-B009-...
    #
    # In the absence of the query parameter we simply return the entire
    # collection.
    #
    # FIXME: This should support pagination!
    sample_name=request.args.get('name')
    if sample_name is not None:
        return jsonize(
            models.get_project_sample(
                {'obfuscated_id': as_id(project)},
                {'name': sample_name},
                False))  # Do not signal a 404 if sample could not be found.
    else:
        return jsonize(
            models.get_samples(
                obfuscated_id=as_id(project)))


@app.route('/projects/<project>/samples/<sample>', methods=['GET'])
def get_project_sample(project, sample):
    return jsonize(
        models.get_project_sample(
            {'obfuscated_id': as_id(project)},
            {'obfuscated_id': as_id(sample)}))


@app.route('/projects/<_>/samples/<sample>/stages', methods=['GET'])
def get_project_sample_stages(_, sample):
    (stages, token) = models.get_sample_stages(as_id(sample))
    return jsonize({'stages': stages, 'token': token})


@app.route('/projects/<_>/samples/<sample>/stages/<stage>', methods=['GET'])
def get_project_sample_stage(_, sample, stage):
    return jsonize(models.get_sample_stages(as_id(sample), as_id(stage)))


@app.route('/projects/<project>/samples/<sample>/stages/<stage>', methods=['PUT'])
@authenticated
def put_project_sample_stage(project, sample, stage, auth_token=None):
    with authz.user_authorization(auth_token):
        method = models.get_method(obfuscated_id=as_id(request.json['method']))
        annotation = request.json['annotation']
        token = stage
        rsp = jsonize(
            models.add_sample_stage(
                as_id(sample), as_id(method.obfuscated_id), annotation, token))
        return (rsp, http.HTTP_201_CREATED)


@app.route('/methods', methods=['GET'])
def get_methods():
    return jsonize(models.get_methods())


@app.route('/methods/<method>', methods=['GET'])
def get_method(method):
    return jsonize(models.get_method(obfuscated_id=as_id(method)))


@app.route('/users/<authenticator>/<uid>', methods=['GET'])
@authenticated
def get_user(uid, authenticator, auth_token=None):
    return jsonize(
        models.get_user_authorization(
            uid, authenticator, abort_not_found=True))


@app.route('/users/add', methods=['PUT'])
@authenticated
def add_user(auth_token=None):
    """
    Add a new user.  The user must have been successfully authenticated by an
    authentication provider supported by Sagittariidae (e.g. Google); this is
    indicated by the presence of a valid `auth_token` in the request data.

    If the request is accepted and succesfully processed, a '202' (Accepted)
    HTTP code is returned.  This indicates that that user is not immediately
    authorized and operations performed by that user may be rejected as
    unauthorized.  Clients may determine whether a user is ready for use by
    polling the user status.
    """
    uid = request.args.get('uid')
    authenticator = request.args.get('authenticator')
    u = models.add_user(uid, authenticator)
    return (jsonize(u), http.HTTP_202_ACCEPTED)

# -------------------------------------- static routes and error handlers --- #

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


@app.errorhandler(Exception)
def unhandled_exception(e):
    app.logger.error('Unhandled exception: %s' % e, exc_info=e)
    raise e

# ------------------------------------------------------ data marshalling --- #

def as_id(resource_name):
    return resource_name.split('-')[0]


class DBModelJSONEncoder(json.JSONEncoder):

    BAD_URI_PAT  = re.compile("%.{2}|\/|_")
    COLLAPSE_PAT = re.compile("-{2,}")

    def __init__(self, **kw):
        super(DBModelJSONEncoder, self).__init__(**kw)

        # This is a terrible hack to make it possible to add context to the
        # stages IDs.  The relative ordering of stages is important, and from
        # this we infer the ordinal position values.  Note this that assumes
        # that a new encoder instance is used for each JSON document; do not
        # cache encoders!
        self.sample_stage_count = 0

    def _uri_name(self, obfuscated_id, name):
        """
        Convert the name of a resource (like a project or sample) into a
        URI-friendly form.  This function has strong opinions about what a
        "good" URI ID is, and will complain if the ID cannot be rendered in
        an acceptable form.  In particular, it should not contain any
        characters that need to be escaped; cf. `urllib.quote()`.
        """
        assert obfuscated_id is not None
        assert name is not None
        # URI-escape special characters
        new_name = quote(name.lower().replace(" ", "-"))
        # Convert escapes into underscores; i.e. foo%20bar -> foo-bar
        new_name = re.sub(self.BAD_URI_PAT, '-', new_name)
        # Collapse multiple consecutive hyphens; i.e. foo---bar -> foo-bar
        new_name = re.sub(self.COLLAPSE_PAT, '-', new_name)
        # concat with the ID and return
        return '-'.join([obfuscated_id, new_name])

    def _dictify(self, model, exclude={}):
        """
        Return a model as a dictionary. 'Private' attributes are removed and
        underscores are replaced with more hyphens in attribute names, making
        for more aesthetically pleasing HTTP data maps.
        """
        def tr(kv):
            return (kv[0].replace('_', '-'), kv[1])
        return dict(tr(kv) for kv in iter(model.__dict__.items())
                    if (not (kv[0].startswith('_') or (kv[0] in exclude))))

    def strip_private_fields(self, d):
        if d.has_key('obfuscated-id'):
            del d['obfuscated-id']
        return d

    def _encodeProject(self, p):
        d = self._dictify(p)
        d['id'] = self._uri_name(d['obfuscated-id'], d['name'])
        return self.strip_private_fields(d)

    def _encodeMethod(self, m):
        d = self._dictify(m)
        d['id'] = self._uri_name(d['obfuscated-id'], d['name'])
        return self.strip_private_fields(d)

    def _encodeSample(self, s):
        d = self._dictify(s, {'project'})
        d['id'] = self._uri_name(d['obfuscated-id'], d['name'])
        d['project'] = self._uri_name(s.project.obfuscated_id, s.project.name)
        return self.strip_private_fields(d)

    def _encodeSampleStage(self, ss):
        d = self._dictify(ss, {'sample', 'method'})
        self.sample_stage_count += 1
        d['id'] = self._uri_name(d['obfuscated-id'], str(self.sample_stage_count))
        d['sample'] = self._uri_name(ss.sample.obfuscated_id, ss.sample.name)
        d['method'] = self._uri_name(ss.method.obfuscated_id, ss.method.name)
        return self.strip_private_fields(d)

    def _encodeUserAuthentication(self, ua):
        return self.strip_private_fields(self._dictify(ua, {'user_authz_id'}))

    def _encodeUserAuthorization(self, ua):
        d = self._dictify(ua, {'authorized'})
        d['id'] = d['obfuscated-id']
        d['authentication-identities'] = ua.authn_identities
        return self.strip_private_fields(d)

    def _encodeModel(self, m):
        return self.strip_private_fields(self._dictify(m))

    def default(self, thing):
        if isinstance(thing, models.Project):
            return self._encodeProject(thing)
        if isinstance(thing, models.Method):
            return self._encodeMethod(thing)
        if isinstance(thing, models.Sample):
            return self._encodeSample(thing)
        if isinstance(thing, models.SampleStage):
            return self._encodeSampleStage(thing)
        if isinstance(thing, models.UserAuthorization):
            return self._encodeUserAuthorization(thing)
        if isinstance(thing, db.Model):
            return self._encodeModel(thing)


def jsonize(x):
    return json.dumps(x, cls=DBModelJSONEncoder)

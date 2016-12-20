
import os
import re

import app.file   as f
import app.models as m

import config

class Annotation(object):
    def __init__(self, a):
        if type(a) is tuple:
            assert len(a) == 2
            self._strval_ = "%s=%s" % a
        elif type(a) is str:
            self._strval_ = a
    def __str__(self):
        return self._strval_

class Datafile(object):
    def __init__(self, path):
        assert f.isfile(path) and f.isreadable(path), "Unreadable path '%s'" % path
        self.path = path

class StageBuilder(object):
    def to_sample(self, oid):
        assert self.method is not None
        assert (self.annotations is not None) and (len(self.annotations) > 0)
        sample = m.get_sample({'obfuscated_id': oid})
        def _makeitso_():
            assert (self.annotations is not None) and (len(self.annotations) > 0)
            stage = m.add_sample_stage(
                sample.obfuscated_id,
                self.method.obfuscated_id,
                ';'.join(map(str, self.annotations)),
                m.get_sample_stages(sample.obfuscated_id)[1])
            for datafile in self.datafiles:
                m.add_file(
                    os.path.relpath(datafile.path, config.UPLOAD_PATH),
                    stage.obfuscated_id)
            return stage
        return _makeitso_
    def with_annotations(self, annotations):
        self.annotations = [Annotation(a) for a in annotations]
        return self
    def with_files(self, paths):
        self.datafiles = [Datafile(p) for p in paths]
        return self
    def with_method(self, oid):
        self.method = m.get_method(obfuscated_id=oid)
        return self

def add_stage():
    return StageBuilder()

# import shell as sh
# st = sh.add_stage()
#      .with_method('m')
#      .with_files(['/foo/bar/baz'])
#      .with_annotations(["tag", ("pkey", "pval")])
#      .to_sample('s')()
## Note: When the cleaner kicks in, the directories in which the files reside
##       will be deleted.  The cleaner assumes that the files have been
##       uploaded (in parts) into its own staging directory.  Make sure that
##       you honour this structure or risk losing data files!

def find(root, rexp):
    pattern = re.compile(rexp)
    matches = []
    def walkerror(e):
        raise e
    for path, dirs, files in os.walk(root, onerror=walkerror):
        matches += filter(lambda p: pattern.search(p) is not None,
                          map(lambda f: os.path.join(path, f), files))
    return matches

def collect(fn, coll):
    m = {}
    for el in coll:
        key = fn(el)
        if m.get(key) == None:
            m[key] = []
        m[key].append(el)
    return m

def parse_fpath(p):
    label = p.split('/')[6]
    return {'label': label, 'path': p}

def project(name):
    s = m.get_project(abort_not_found=False, obfuscated_id=name)
    if s is None:
        s = m.get_project(abort_not_found=False, name=name)
    if s is None:
        raise Exception("'%s' matches no known project ID or name." % name)
    else:
        return s

def sample(name):
    s = m.get_sample({'obfuscated_id': name}, abort_not_found=False)
    if s is None:
        s = m.get_sample({'name': name}, abort_not_found=False)
    if s is None:
        raise Exception("'%s' matches no known sample ID or name." % name)
    else:
        return s

def stage_builder(method, label, files):
    st = add_stage().with_method(method)
    parts = label.split('-')
    if len(parts) > 1:
        st.with_annotations([parts[1]])
    st.with_files(files)
    return st.to_sample(sample(parts[0]).obfuscated_id)

if __name__ == "__example__":
    import app
    import app.models as m
    import config
    import os

    root = '/mnt/adapt/analysis/inconel/versa-data/P001-B001/Uncompressed'
    project = 'PqrX9'
    method = 'XZOQ0'
    labelled = collect(lambda m: m['label'], map(parse_fpath, find(root, '^((?!.*Multiple_Images).)*\.(xrm|txm|txrm|tar|tif|avi)$')))

    errors = []

    for s in map(lambda x: x.split('-')[0], labelled.keys()):
        try:
            m.add_sample(project, s)
        except Exception as e:
            errors.append(e)

    upload_root = config.UPLOAD_PATH
    builders = [stage_builder(method, label, map(lambda m: m['path'], labelled[label])) for label in labelled.keys()]
    errors = []
    for builderfn in builders:
        try:
            builderfn()
        except Exception as e:
            errors.append(e)

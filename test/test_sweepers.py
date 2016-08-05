
import os
import pytest

import app          as sagittariidae
import app.models   as models
import app.sweepers as sweepers

from fixtures import *


def touch(fname):
    os.makedirs(os.path.dirname(fname))
    open(fname, 'wa').close()


@pytest.fixture(scope='function')
def stage_file(storepath, sample_with_stages):
    ssf = models.add_file(
        'uploaded-file', sample_with_stages['stages'][0].obfuscated_id)
    src_fname = os.path.join(
        sagittariidae.app.app.config['UPLOAD_PATH'], ssf.relative_source_path)
    tgt_fname = os.path.join(
        sagittariidae.app.app.config['STORE_PATH'], ssf.relative_target_path)
    return {'model'  : ssf,
            'source' : src_fname,
            'target' : tgt_fname}


def test_SampleStageFileSweeper_move_file(sample_with_stages, stage_file):
    touch(stage_file['source'])
    stage = sample_with_stages['stages'][0]

    # Sanity checks to make sure that the world is in a valid starting, and not
    # accidentally already the state into which we want it set.
    assert os.path.isfile(stage_file['source']), "Source file is missing."
    assert not os.path.isfile(stage_file['target']), "Target file found; unexpected."
    exp_status = models.FileStatus.incomplete
    act_status  = models.get_files(sample_stage_id=stage.obfuscated_id, status=exp_status)[0].status
    assert exp_status == act_status

    # Be the change you want to see.
    sweepers.make_sweeper(sweepers.SampleStageFileSweeper).sweep()

    # Validate the world has become a better place.  (If only it were that easy
    # IRL.)
    assert os.path.isfile(stage_file['target']), "Target file not created."
    exp_status = models.FileStatus.complete
    act_status = models.get_files(sample_stage_id=stage.obfuscated_id, status=exp_status)[0].status
    assert exp_status == act_status

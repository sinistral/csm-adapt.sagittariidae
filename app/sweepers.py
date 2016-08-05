
"""
This module contains the definitions of Sagittariidae's sweeper processes.
These are asynchronous processes that designed to drive the current state of
the world to a desired final state.

The sweepers are run as processes separate from the webservice.  They may be
invoked by name by executing this module, typically from a scheduler such as
`cron`.
"""

import os
import shutil
import sys

import app as sagittariidae
import models


logger = sagittariidae.app.logger

class Sweeper(object):

    def run(self):
        raise NotImplementedError()

    def sweep(self):
        try:
            self.run()
        except Exception, e:
            logger.error('Unhandled exception in sweeper %s', self, exc_info=e)


class SampleStageFileSweeper(Sweeper):

    def _complete_(self, ssf):
        config   = sagittariidae.app.config
        src_path = os.path.join(config['UPLOAD_PATH'], ssf.relative_source_path)
        tgt_path = os.path.join(config['STORE_PATH'], ssf.relative_target_path)
        tgt_dir  = os.path.dirname(tgt_path)
        if not os.path.isdir(tgt_dir):
            os.makedirs(tgt_dir)
        shutil.move(src_path, tgt_path)
        logger.info('Moved file: %s -> %s', src_path, tgt_path)
        models.complete_file(ssf)

    def run(self):
        logger = sagittariidae.app.logger

        files = models.get_files(
            sample_stage_id=None,
            status=models.FileStatus.incomplete)
        logger.info('Found %d incomplete files: %s', len(files), files)
        for f in files:
            try:
                self._complete_(f)
            except Exception, e:
                logger.error('Error moving file %s', f, exc_info=e)


def make_sweeper(c):
    try:
        if c == Sweeper:
            raise Exception('Not a sweeper impl %s' % c)
        i = c()
        if not isinstance(i, Sweeper):
            raise Exception('%s is not an implementation of %s' % (c, Sweeper))
        else:
            return i
    except Exception, e:
        logger.error('Invalid sweeper class %s', sys.argv[1], exc_info=e)
        raise e


if __name__ == '__main__':
    make_sweeper(globals().get(sys.argv[1])).sweep()

# Copyright (C) 2007 Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""Logging service setup.

STABLE.
"""

import six
import errno
import logging
import sys
import os
import time

from six.moves import reprlib as repr_
from sugar3 import env

# Let's keep this module self contained so that it can be easily
# pasted in external sugar service like the datastore.

_LEVELS = {
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'all': 0,
}

# DEPRECATED
def get_logs_dir():
    return env.get_logs_path()


def set_level(level):
    if level in _LEVELS:
        logging.getLogger('').setLevel(_LEVELS[level])
        return

    try:
        logging.getLogger('').setLevel(int(level))
    except ValueError:
        logging.warning('Invalid log level: %r' % level)


def cleanup():
    """Clean up the log directory, moving old logs into a numbered backup
    directory.  We only keep `_MAX_BACKUP_DIRS` of these backup directories
    around; the rest are removed."""
    logs_dir = get_logs_dir()

    if not os.path.isdir(logs_dir):
        os.makedirs(logs_dir)

    backup_logs = []
    backup_dirs = []
    for f in os.listdir(logs_dir):
        path = os.path.join(logs_dir, f)
        if os.path.isfile(path):
            backup_logs.append(f)
        elif os.path.isdir(path):
            backup_dirs.append(path)

    if len(backup_dirs) > 3:
        backup_dirs.sort()
        root = backup_dirs[0]

        try:
            for f in os.listdir(root):
                os.remove(os.path.join(root, f))
            os.rmdir(root)
        except OSError as e:
            print("Could not remove old logs files %s" % e)

    if len(backup_logs) > 0:
        name = str(int(time.time()))
        backup_dir = os.path.join(logs_dir, name)
        try:
            os.mkdir(backup_dir)
            for log in backup_logs:
                source_path = os.path.join(logs_dir, log)
                dest_path = os.path.join(backup_dir, log)
                os.rename(source_path, dest_path)
        except OSError as e:
            # gracefully deal w/ disk full
            if e.errno != errno.ENOSPC:
                raise e


def start(log_filename=None):
    logs_path = env.get_logs_path()

    try:
        os.makedirs(logs_path)
    except OSError:
        pass

    # remove existing handlers, or logging.basicConfig() won't have no effect.
    root_logger = logging.getLogger('')
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)

    class SafeLogWrapper(object):
        """Small file-like wrapper to gracefully handle ENOSPC errors when
        logging."""

        def __init__(self, stream):
            self._stream = stream

        def write(self, s):
            try:
                self._stream.write(s)
            except IOError as e:
                # gracefully deal w/ disk full
                if e.errno != errno.ENOSPC:
                    raise e

        def flush(self):
            try:
                self._stream.flush()
            except IOError as e:
                # gracefully deal w/ disk full
                if e.errno != errno.ENOSPC:
                    raise e

    logging.basicConfig(
        level=logging.WARNING,
        format="%(created)f %(levelname)s %(name)s: %(message)s",
        stream=SafeLogWrapper(sys.stderr))

    if 'SUGAR_LOGGER_LEVEL' in os.environ:
        set_level(os.environ['SUGAR_LOGGER_LEVEL'])

    if log_filename:
        try:
            log_path = os.path.join(logs_path, log_filename + '.log')

            log_fd = os.open(log_path, os.O_WRONLY | os.O_CREAT)
            os.dup2(log_fd, sys.stdout.fileno())
            os.dup2(log_fd, sys.stderr.fileno())
            os.close(log_fd)

            sys.stdout = SafeLogWrapper(sys.stdout)
            sys.stderr = SafeLogWrapper(sys.stderr)
        except OSError as e:
            # if we're out of space, just continue
            if e.errno != errno.ENOSPC:
                raise e



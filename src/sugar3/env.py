"""Calculates file-paths for the Sugar working environment"""
# Copyright (C) 2006-2007 Red Hat, Inc.
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

"""
STABLE.
"""

import logging
import os


# DEPRECATED
def is_emulator():
    logging.error("sugar.env.is_emulator is deprecated")
    return False


def get_profile_path(path=None):
    profile_id = os.environ.get('SUGAR_PROFILE', 'default')
    home_dir = os.environ.get('SUGAR_HOME', os.path.expanduser('~/.sugar'))
    base = os.path.join(home_dir, profile_id)
    if not os.path.isdir(base):
        try:
            os.makedirs(base, 0o770)
        except OSError:
            print('Could not create user directory.')

    if path is not None:
        return os.path.join(base, path)
    else:
        return base


def get_logs_path(path=None):
    base = os.environ.get('SUGAR_LOGS_DIR', get_profile_path('logs'))
    if path is not None:
        return os.path.join(base, path)
    else:
        return base


def get_user_activities_path():
    return os.environ.get("SUGAR_ACTIVITIES_PATH",
                          os.path.expanduser('~/Activities'))


def get_user_library_path():
    return os.environ.get("SUGAR_LIBRARY_PATH",
                          os.path.expanduser('~/Library'))

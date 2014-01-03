# Copyright (C) 2012, Daniel Narvaez
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
UNSTABLE.
"""

from __future__ import absolute_import

import logging
import os
import unittest
import subprocess
from contextlib import contextmanager

from sugar3.test import uitree

import dbus
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()


class UITestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        unittest.TestCase(self, *args, **kwargs)

        self.bundle_id = None

    def setUp(self):
        logger = logging.getLogger()
        self._orig_level = logger.getEffectiveLevel()
        logger.setLevel(logging.DEBUG)

    def tearDown(self):
        logger = logging.getLogger()
        logger.setLevel(self._orig_level)

    @contextmanager
    def run_view(self, name):
        view_path = os.path.join("views", "%s.py" % name)
        process = subprocess.Popen(["python", view_path])

        try:
            yield
        except:
            logging.debug(uitree.get_root().dump())
            raise
        finally:
            process.terminate()

    @contextmanager
    def run_activity(self):
        if self.bundle_id is not None:
            process = subprocess.Popen(["sugar-launch", self.bundle_id])
        else:
            print "No bundle_id specified."
            return

        try:
            yield
        except:
            logging.debug(uitree.get_root().dump())
            raise
        finally:
            process.terminate()

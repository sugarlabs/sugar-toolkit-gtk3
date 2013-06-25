# Copyright (C) 2013, One Laptop per Child
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

import os
import unittest
import subprocess

from sugar3.bundle import bundle_from_dir, bundle_from_archive
from sugar3.bundle.activitybundle import ActivityBundle
from sugar3.bundle.contentbundle import ContentBundle

tests_dir = os.path.dirname(__file__)
data_dir = os.path.join(tests_dir, "data")
SAMPLE_ACTIVITY_PATH = os.path.join(data_dir, 'sample.activity')
SAMPLE_CONTENT_PATH = os.path.join(data_dir, 'sample.content')


class TestBundle(unittest.TestCase):
    def test_bundle_from_dir(self):
        bundle = bundle_from_dir(SAMPLE_ACTIVITY_PATH)
        self.assertIsInstance(bundle, ActivityBundle)
        bundle = bundle_from_dir(SAMPLE_CONTENT_PATH)
        self.assertIsInstance(bundle, ContentBundle)

    def test_activity_bundle_from_archive(self):
        os.chdir(SAMPLE_ACTIVITY_PATH)
        subprocess.check_call(["./setup.py", "dist_xo"])
        xo_path = os.path.join(".", "dist", "Sample-1.xo")
        bundle = bundle_from_archive(xo_path)
        self.assertIsInstance(bundle, ActivityBundle)

    def test_content_bundle_from_archive(self):
        os.chdir(data_dir)
        subprocess.check_call(["zip", "-r", "sample-1.xol", "sample.content"])
        bundle = bundle_from_archive("./sample-1.xol")
        self.assertIsInstance(bundle, ContentBundle)

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

import os
import unittest
import shutil
import subprocess
import tempfile
import tarfile
import zipfile

tests_dir = os.path.dirname(__file__)
data_dir = os.path.join(tests_dir, "data")


class TestGit(unittest.TestCase):
    _source_files = ["activity.py",
                     "setup.py",
                     "po/Sample.pot",
                     "po/es.po",
                     "activity/activity.info",
                     "activity/activity-sample.svg"]

    _activity_locale_files = ["locale/es/activity.linfo"]

    _share_locale_files = ["locale/es/LC_MESSAGES/org.sugarlabs.Sample.mo"]

    def _get_all_locale_files(self):
        expected = self._share_locale_files[:]
        expected.extend(self._activity_locale_files)
        return expected

    def _create_repo(self):
        cwd = os.getcwd()
        path = tempfile.mkdtemp()
        os.chdir(path)

        subprocess.check_call(["git", "init"])
        subprocess.check_call(["git", "config", "user.name", "Test Test"])
        subprocess.check_call(["git", "config", "user.email", "test@test.org"])

        for source in self._source_files:
            source_path = os.path.join(data_dir, "sample.activity", source)
            dest_path = os.path.join(path, source)

            try:
                os.makedirs(os.path.dirname(dest_path))
            except OSError:
                pass

            shutil.copyfile(source_path, dest_path)
            shutil.copymode(source_path, dest_path)

            subprocess.check_call(["git", "add", source])

        subprocess.check_call(["git", "commit", "-m", "Initial commit", "-a"])

        os.chdir(cwd)

        return path

    def _strip_root_dir(self, paths):
        return [path[path.find("/") + 1:] for path in paths]

    def _test_dist_xo(self, source_path, build_path):
        cwd = os.getcwd()
        os.chdir(build_path)

        setup_path = os.path.join(source_path, "setup.py")
        subprocess.call([setup_path, "dist_xo"])

        xo_path = os.path.join(build_path, "dist", "Sample-1.xo")
        filenames = zipfile.ZipFile(xo_path).namelist()

        stripped_filenames = self._strip_root_dir(filenames)
        expected = self._source_files[:]
        expected.extend(self._get_all_locale_files())
        self.assertItemsEqual(stripped_filenames, expected)

        os.chdir(cwd)

    def _test_dist_source(self, source_path, build_path):
        cwd = os.getcwd()
        os.chdir(build_path)

        setup_path = os.path.join(source_path, "setup.py")
        subprocess.call([setup_path, "dist_source"])

        xo_path = os.path.join(build_path, "dist", "Sample-1.tar.bz2")
        filenames = tarfile.open(name=xo_path, mode="r:bz2").getnames()

        stripped_filenames = self._strip_root_dir(filenames)
        self.assertItemsEqual(stripped_filenames, self._source_files)

        os.chdir(cwd)

    def _test_build(self, source_path, build_path):
        cwd = os.getcwd()
        os.chdir(build_path)

        setup_path = os.path.join(source_path, "setup.py")
        subprocess.call([setup_path, "build"])

        locale_path = os.path.join(build_path, "locale")

        filenames = []
        for root, dirs, files in os.walk(locale_path):
            rel_root = root[len(build_path) + 1:]
            filenames.extend([os.path.join(rel_root, name) for name in files])

        self.assertItemsEqual(filenames, self._get_all_locale_files())

        os.chdir(cwd)

    def _test_dev(self, source_path, build_path):
        activities_path = tempfile.mkdtemp()

        cwd = os.getcwd()
        os.chdir(build_path)

        os.environ["SUGAR_ACTIVITIES_PATH"] = activities_path

        setup_path = os.path.join(source_path, "setup.py")
        subprocess.call([setup_path, "dev"])

        activity_py_path = os.path.join(activities_path, "Sample.activity",
                                        "activity.py")
        self.assertTrue(os.path.exists(activity_py_path))

        os.chdir(cwd)

    def _test_genpot(self, source_path, build_path):
        cwd = os.getcwd()
        os.chdir(build_path)

        pot_path = os.path.join(source_path, "po", "Sample.pot")
        os.unlink(pot_path)

        setup_path = os.path.join(source_path, "setup.py")
        subprocess.call([setup_path, "genpot"])

        self.assertTrue(os.path.exists(pot_path))

        os.chdir(cwd)

    def _test_install(self, source_path, build_path):
        install_path = tempfile.mkdtemp()

        cwd = os.getcwd()
        os.chdir(build_path)

        setup_path = os.path.join(source_path, "setup.py")
        subprocess.call([setup_path, "install", "--prefix", install_path])

        filenames = []
        activity_dir = os.path.join(install_path, "share",
                                    "sugar", "activities", "Sample.activity")
        for root, dirs, files in os.walk(activity_dir):
            rel_root = root[len(activity_dir) + 1:]
            filenames.extend([os.path.join(rel_root, name) for name in files])

        expected = self._source_files[:]
        expected.extend(self._activity_locale_files)

        self.assertItemsEqual(filenames, expected)

        filenames = []
        share_dir = os.path.join(install_path, "share")
        locale_dir = os.path.join(share_dir, "locale")
        for root, dirs, files in os.walk(locale_dir):
            rel_root = root[len(share_dir) + 1:]
            for name in files:
                if "org.sugarlabs.Sample" in name:
                    filenames.append(os.path.join(rel_root, name))

        self.assertItemsEqual(filenames, self._share_locale_files)

        os.chdir(cwd)

    def test_dist_xo_in_source(self):
        repo_path = self._create_repo()
        self._test_dist_xo(repo_path, repo_path)

    def test_dist_xo_out_of_source(self):
        repo_path = self._create_repo()
        build_path = tempfile.mkdtemp()
        self._test_dist_xo(repo_path, build_path)

    def test_dist_source_in_source(self):
        repo_path = self._create_repo()
        self._test_dist_source(repo_path, repo_path)

    def test_dist_source_out_of_source(self):
        repo_path = self._create_repo()
        build_path = tempfile.mkdtemp()
        self._test_dist_source(repo_path, build_path)

    def test_install_in_source(self):
        repo_path = self._create_repo()
        self._test_install(repo_path, repo_path)

    def test_install_out_of_source(self):
        repo_path = self._create_repo()
        build_path = tempfile.mkdtemp()
        self._test_install(repo_path, build_path)

    def test_build_in_source(self):
        repo_path = self._create_repo()
        self._test_build(repo_path, repo_path)

    def test_build_out_of_source(self):
        repo_path = self._create_repo()
        build_path = tempfile.mkdtemp()
        self._test_build(repo_path, build_path)

    def test_dev_in_source(self):
        repo_path = self._create_repo()
        self._test_genpot(repo_path, repo_path)

    def test_dev_out_of_source(self):
        repo_path = self._create_repo()
        build_path = tempfile.mkdtemp()
        self._test_dev(repo_path, build_path)

    def test_genpot_in_source(self):
        repo_path = self._create_repo()
        self._test_genpot(repo_path, repo_path)

    def test_genpot_out_of_source(self):
        repo_path = self._create_repo()
        build_path = tempfile.mkdtemp()
        self._test_genpot(repo_path, build_path)

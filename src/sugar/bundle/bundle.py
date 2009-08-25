# Copyright (C) 2007, Red Hat, Inc.
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

"""Sugar bundle file handler

UNSTABLE.
"""

import os
import logging
import shutil
import StringIO
import zipfile


class AlreadyInstalledException(Exception):
    pass


class NotInstalledException(Exception):
    pass


class InvalidPathException(Exception):
    pass


class ZipExtractException(Exception):
    pass


class RegistrationException(Exception):
    pass


class MalformedBundleException(Exception):
    pass


class Bundle(object):
    """A Sugar activity, content module, etc.

    The bundle itself may be either a zip file or a directory
    hierarchy, with metadata about the bundle stored various files
    inside it.

    This is an abstract base class. See ActivityBundle and
    ContentBundle for more details on those bundle types.
    """

    _zipped_extension = None
    _unzipped_extension = None

    def __init__(self, path):
        self._path = path
        self._zip_root_dir = None

        if os.path.isdir(self._path):
            self._zip_file = None
        else:
            self._zip_file = zipfile.ZipFile(self._path)
            self._check_zip_bundle()

        # manifest = self._get_file(self._infodir + '/contents')
        # if manifest is None:
        #     raise MalformedBundleException('No manifest file')

        # signature = self._get_file(self._infodir + '/contents.sig')
        # if signature is None:
        #     raise MalformedBundleException('No signature file')

    def __del__(self):
        if self._zip_file is not None:
            self._zip_file.close()

    def _check_zip_bundle(self):
        file_names = self._zip_file.namelist()
        if len(file_names) == 0:
            raise MalformedBundleException('Empty zip file')

        if file_names[0] == 'mimetype':
            del file_names[0]

        self._zip_root_dir = file_names[0].split('/')[0]
        if self._zip_root_dir.startswith('.'):
            raise MalformedBundleException(
                'root directory starts with .')
        if self._unzipped_extension is not None:
            (name_, ext) = os.path.splitext(self._zip_root_dir)
            if ext != self._unzipped_extension:
                raise MalformedBundleException(
                    'All files in the bundle must be inside a single ' +
                    'directory whose name ends with "%s"' %
                    self._unzipped_extension)

        for file_name in file_names:
            if not file_name.startswith(self._zip_root_dir):
                raise MalformedBundleException(
                    'All files in the bundle must be inside a single ' +
                    'top-level directory')

    def get_file(self, filename):
        f = None

        if self._zip_file is None:
            path = os.path.join(self._path, filename)
            try:
                f = open(path, "rb")
            except IOError:
                return None
        else:
            path = os.path.join(self._zip_root_dir, filename)
            try:
                data = self._zip_file.read(path)
                f = StringIO.StringIO(data)
            except KeyError:
                logging.debug('%s not found.', filename)

        return f

    def is_file(self, filename):
        if self._zip_file is None:
            path = os.path.join(self._path, filename)
            return os.path.isfile(path)
        else:
            path = os.path.join(self._zip_root_dir, filename)
            try:
                self._zip_file.getinfo(path)
            except KeyError:
                return False

            return True

    def is_dir(self, filename):
        if self._zip_file is None:
            path = os.path.join(self._path, filename)
            return os.path.isdir(path)
        else:
            path = os.path.join(self._zip_root_dir, filename, "")
            for f in self._zip_file.namelist():
                if f.startswith(path):
                    return True
            return False

    def get_path(self):
        """Get the bundle path."""
        return self._path

    def _unzip(self, install_dir):
        if self._zip_file is None:
            raise AlreadyInstalledException

        if not os.path.isdir(install_dir):
            os.mkdir(install_dir, 0775)

        # zipfile provides API that in theory would let us do this
        # correctly by hand, but handling all the oddities of
        # Windows/UNIX mappings, extension attributes, deprecated
        # features, etc makes it impractical.
        # FIXME: use manifest
        if os.spawnlp(os.P_WAIT, 'unzip', 'unzip', '-o', self._path,
                      '-x', 'mimetype', '-d', install_dir):
            # clean up install dir after failure
            shutil.rmtree(os.path.join(install_dir, self._zip_root_dir),
                          ignore_errors=True)
            # indicate failure.
            raise ZipExtractException

    def _zip(self, bundle_path):
        if self._zip_file is not None:
            raise NotInstalledException

        raise NotImplementedError

    def _uninstall(self, install_path):
        if not os.path.isdir(install_path):
            raise InvalidPathException
        if self._unzipped_extension is not None:
            (name_, ext) = os.path.splitext(install_path)
            if ext != self._unzipped_extension:
                raise InvalidPathException

        for root, dirs, files in os.walk(install_path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                path = os.path.join(root, name)
                if os.path.islink(path):
                    os.remove(path)
                else:
                    os.rmdir(path)
        os.rmdir(install_path)

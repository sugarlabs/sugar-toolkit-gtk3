# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2009 Aleksey Lim
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

"""Sugar content bundles

UNSTABLE.
"""

from six.moves import urllib
from six.moves.configparser import ConfigParser

import tempfile
import os

from sugar3 import env
from sugar3.bundle.bundle import Bundle, MalformedBundleException

from sugar3.bundle.bundleversion import NormalizedVersion
from sugar3.bundle.bundleversion import InvalidVersionError


class ContentBundle(Bundle):
    """A Sugar content bundle

    See http://wiki.laptop.org/go/Content_bundles for details
    """

    MIME_TYPE = 'application/vnd.olpc-content'

    _zipped_extension = '.xol'
    _unzipped_extension = None
    _infodir = 'library'

    def __init__(self, path):
        Bundle.__init__(self, path)

        self._locale = None
        self._name = None
        self._icon = None
        self._library_version = '0'
        self._activity_start = 'index.html'
        self._global_name = None

        info_file = self.get_file('library/library.info')
        if info_file is None:
            raise MalformedBundleException('No library.info file')
        self._parse_info(info_file)

        if self.get_file(self._activity_start) is None:
            raise MalformedBundleException(
                'Content bundle %s does not have start page %s' %
                (self._path, self._activity_start))

    def _parse_info(self, info_file):
        cp = ConfigParser()
        cp.readfp(info_file)

        section = 'Library'

        if cp.has_option(section, 'name'):
            self._name = cp.get(section, 'name')
        else:
            raise MalformedBundleException(
                'Content bundle %s does not specify a name' % self._path)

        if cp.has_option(section, 'library_version'):
            version = cp.get(section, 'library_version')
            try:
                NormalizedVersion(version)
            except InvalidVersionError:
                raise MalformedBundleException(
                    'Content bundle %s has invalid version number %s' %
                    (self._path, version))
            self._library_version = version

        if cp.has_option(section, 'locale'):
            self._locale = cp.get(section, 'locale')

        if cp.has_option(section, 'global_name'):
            self._global_name = cp.get(section, 'global_name')

        if cp.has_option(section, 'icon'):
            self._icon = cp.get(section, 'icon')

        # Compatibility with old content bundles
        if self._global_name is not None \
                and cp.has_option(section, 'bundle_class'):
            self._global_name = cp.get(section, 'bundle_class')

        if cp.has_option(section, 'activity_start'):
            self._activity_start = cp.get(section, 'activity_start')

        if self._global_name is None:
            raise MalformedBundleException(
                'Content bundle %s must specify global_name' % self._path)

    def get_name(self):
        return self._name

    def get_library_version(self):
        return self._library_version

    def get_locale(self):
        return self._locale

    def get_activity_start(self):
        return self._activity_start

    def get_icon(self):
        if not self._icon:
            return None

        icon_path = os.path.join('library', self._icon)
        ext = os.path.splitext(icon_path)[1]
        if ext == '':
            ext = '.svg'
            icon_path += ext

        if self._zip_file is None:
            return os.path.join(self._path, icon_path)
        else:
            icon_data = self.get_file(icon_path).read()
            temp_file, temp_file_path = tempfile.mkstemp(prefix=self._icon,
                                                         suffix=ext)
            os.write(temp_file, icon_data)
            os.close(temp_file)
            return temp_file_path

    def get_start_uri(self):
        path = os.path.join(self.get_path(), self._activity_start)
        return 'file://' + urllib.request.pathname2url(path)

    def get_bundle_id(self):
        return self._global_name

    def get_activity_version(self):
        return self._library_version

    def get_tags(self):
        return None

    def install(self):
        install_path = env.get_user_library_path()
        self._unzip(install_path)
        return os.path.join(install_path, self._zip_root_dir)

    def uninstall(self, force=False, delete_profile=False):
        install_dir = self._path
        self._uninstall(install_dir)

    def is_user_activity(self):
        # All content bundles are installed in user storage
        return True

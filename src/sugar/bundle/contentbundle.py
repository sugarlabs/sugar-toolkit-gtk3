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

from ConfigParser import ConfigParser
import os
import urllib

from sugar import env
from sugar.bundle.bundle import Bundle, NotInstalledException, \
    MalformedBundleException


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
        self._l10n = None
        self._category = None
        self._name = None
        self._subcategory = None
        self._category_class = None
        self._category_icon = None
        self._library_version = None
        self._bundle_class = None
        self._activity_start = None
        self._global_name = None

        info_file = self.get_file('library/library.info')
        if info_file is None:
            raise MalformedBundleException('No library.info file')
        self._parse_info(info_file)

        if (self.get_file('index.html') is None and
            self.get_file('library/library.xml') is None):
            raise MalformedBundleException(
                'Content bundle %s has neither index.html nor library.xml' %
                self._path)

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
                self._library_version = int(version)
            except ValueError:
                raise MalformedBundleException(
                    'Content bundle %s has invalid version number %s' %
                    (self._path, version))

        if cp.has_option(section, 'l10n'):
            l10n = cp.get(section, 'l10n')
            if l10n == 'true':
                self._l10n = True
            elif l10n == 'false':
                self._l10n = False
            else:
                raise MalformedBundleException(
                    'Content bundle %s has invalid l10n key "%s"' %
                    (self._path, l10n))
        else:
            raise MalformedBundleException(
                'Content bundle %s does not specify if it is localized' %
                self._path)

        if cp.has_option(section, 'locale'):
            self._locale = cp.get(section, 'locale')
        else:
            raise MalformedBundleException(
                'Content bundle %s does not specify a locale' % self._path)

        if cp.has_option(section, 'category'):
            self._category = cp.get(section, 'category')
        else:
            raise MalformedBundleException(
                'Content bundle %s does not specify a category' % self._path)

        if cp.has_option(section, 'global_name'):
            self._global_name = cp.get(section, 'global_name')
        else:
            self._global_name = None

        if cp.has_option(section, 'category_icon'):
            self._category_icon = cp.get(section, 'category_icon')
        else:
            self._category_icon = None

        if cp.has_option(section, 'category_class'):
            self._category_class = cp.get(section, 'category_class')
        else:
            self._category_class = None

        if cp.has_option(section, 'subcategory'):
            self._subcategory = cp.get(section, 'subcategory')
        else:
            self._subcategory = None

        if cp.has_option(section, 'bundle_class'):
            self._bundle_class = cp.get(section, 'bundle_class')
        else:
            self._bundle_class = None

        if cp.has_option(section, 'activity_start'):
            self._activity_start = cp.get(section, 'activity_start')
        else:
            self._activity_start = 'index.html'

        if self._bundle_class is None and self._global_name is None:
            raise MalformedBundleException(
                'Content bundle %s must specify either global_name or '
                'bundle_class' % self._path)

    def get_name(self):
        return self._name

    def get_library_version(self):
        return self._library_version

    def get_l10n(self):
        return self._l10n

    def get_locale(self):
        return self._locale

    def get_category(self):
        return self._category

    def get_category_icon(self):
        return self._category_icon

    def get_category_class(self):
        return self._category_class

    def get_subcategory(self):
        return self._subcategory

    def get_bundle_class(self):
        return self._bundle_class

    def get_activity_start(self):
        return self._activity_start

    def _run_indexer(self):
        xdg_data_dirs = os.getenv('XDG_DATA_DIRS',
                                  '/usr/local/share/:/usr/share/')
        for path in xdg_data_dirs.split(':'):
            indexer = os.path.join(path, 'library-common', 'make_index.py')
            if os.path.exists(indexer):
                os.spawnlp(os.P_WAIT, 'python', 'python', indexer)

    def get_root_dir(self):
        return os.path.join(env.get_user_library_path(), self._zip_root_dir)

    def get_start_path(self):
        return os.path.join(self.get_root_dir(), self._activity_start)

    def get_start_uri(self):
        return "file://" + urllib.pathname2url(self.get_start_path())

    def get_bundle_id(self):
        # TODO treat ContentBundle in special way
        # needs rethinking while fixing ContentBundle support
        if self._bundle_class is not None:
            return self._bundle_class
        else:
            return self._global_name

    def get_activity_version(self):
        # TODO treat ContentBundle in special way
        # needs rethinking while fixing ContentBundle support
        return self._library_version

    def is_installed(self):
        if self._zip_file is None:
            return True
        elif os.path.isdir(self.get_root_dir()):
            return ContentBundle(self.get_root_dir()).get_library_version() \
                    == self.get_library_version()
        else:
            return False

    def install(self, install_path):
        # TODO ignore passed install_path argument
        # needs rethinking while fixing ContentBundle support
        install_path = env.get_user_library_path()
        self._unzip(install_path)
        self._run_indexer()
        return self.get_root_dir()

    def uninstall(self):
        if self._zip_file is None:
            if not self.is_installed():
                raise NotInstalledException
            install_dir = self._path
        else:
            install_dir = os.path.join(self.get_root_dir())
        self._uninstall(install_dir)
        self._run_indexer()

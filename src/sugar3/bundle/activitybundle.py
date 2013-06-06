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

"""Sugar activity bundles

UNSTABLE.
"""

from ConfigParser import ConfigParser
from locale import normalize
import os
import shutil
import tempfile
import logging

from sugar3 import env
from sugar3.bundle.bundle import Bundle, \
    MalformedBundleException, NotInstalledException
from sugar3.bundle.bundleversion import NormalizedVersion
from sugar3.bundle.bundleversion import InvalidVersionError


def _expand_lang(locale):
    # Private method from gettext.py
    locale = normalize(locale)
    COMPONENT_CODESET = 1 << 0
    COMPONENT_TERRITORY = 1 << 1
    COMPONENT_MODIFIER = 1 << 2

    # split up the locale into its base components
    mask = 0
    pos = locale.find('@')
    if pos >= 0:
        modifier = locale[pos:]
        locale = locale[:pos]
        mask |= COMPONENT_MODIFIER
    else:
        modifier = ''

    pos = locale.find('.')
    if pos >= 0:
        codeset = locale[pos:]
        locale = locale[:pos]
        mask |= COMPONENT_CODESET
    else:
        codeset = ''

    pos = locale.find('_')
    if pos >= 0:
        territory = locale[pos:]
        locale = locale[:pos]
        mask |= COMPONENT_TERRITORY
    else:
        territory = ''

    language = locale
    ret = []
    for i in range(mask + 1):
        if not (i & ~mask):  # if all components for this combo exist ...
            val = language
            if i & COMPONENT_TERRITORY:
                val += territory
            if i & COMPONENT_CODESET:
                val += codeset
            if i & COMPONENT_MODIFIER:
                val += modifier
            ret.append(val)
    ret.reverse()
    return ret


class ActivityBundle(Bundle):
    """A Sugar activity bundle

    See http://wiki.laptop.org/go/Activity_bundles for details
    """

    MIME_TYPE = 'application/vnd.olpc-sugar'

    _zipped_extension = '.xo'
    _unzipped_extension = '.activity'
    _infodir = 'activity'

    def __init__(self, path, translated=True):
        Bundle.__init__(self, path)
        self.activity_class = None
        self.bundle_exec = None

        self._name = None
        self._icon = None
        self._bundle_id = None
        self._mime_types = None
        self._show_launcher = True
        self._tags = None
        self._activity_version = '0'
        self._installation_time = os.stat(path).st_mtime
        self._summary = None

        info_file = self.get_file('activity/activity.info')
        if info_file is None:
            raise MalformedBundleException('No activity.info file')
        self._parse_info(info_file)

        if translated:
            linfo_file = self._get_linfo_file()
            if linfo_file:
                self._parse_linfo(linfo_file)

    def _parse_info(self, info_file):
        cp = ConfigParser()
        cp.readfp(info_file)

        section = 'Activity'

        if cp.has_option(section, 'bundle_id'):
            self._bundle_id = cp.get(section, 'bundle_id')
        else:
            raise MalformedBundleException(
                'Activity bundle %s does not specify a bundle id' %
                self._path)

        if cp.has_option(section, 'name'):
            self._name = cp.get(section, 'name')
        else:
            raise MalformedBundleException(
                'Activity bundle %s does not specify a name' % self._path)

        if cp.has_option(section, 'exec'):
            self.bundle_exec = cp.get(section, 'exec')
        else:
            raise MalformedBundleException(
                'Activity bundle %s must specify either class or exec' %
                self._path)

        if cp.has_option(section, 'mime_types'):
            mime_list = cp.get(section, 'mime_types').strip(';')
            self._mime_types = [mime.strip() for mime in mime_list.split(';')]

        if cp.has_option(section, 'show_launcher'):
            if cp.get(section, 'show_launcher') == 'no':
                self._show_launcher = False

        if cp.has_option(section, 'tags'):
            tag_list = cp.get(section, 'tags').strip(';')
            self._tags = [tag.strip() for tag in tag_list.split(';')]

        if cp.has_option(section, 'icon'):
            self._icon = cp.get(section, 'icon')

        if cp.has_option(section, 'activity_version'):
            version = cp.get(section, 'activity_version')
            try:
                NormalizedVersion(version)
            except InvalidVersionError:
                raise MalformedBundleException(
                    'Activity bundle %s has invalid version number %s' %
                    (self._path, version))
            self._activity_version = version

        if cp.has_option(section, 'summary'):
            self._summary = cp.get(section, 'summary')

    def _get_linfo_file(self):
        # Using method from gettext.py, first find languages from environ
        languages = []
        for envar in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
            val = os.environ.get(envar)
            if val:
                languages = val.split(':')
                break

        # Next, normalize and expand the languages
        nelangs = []
        for lang in languages:
            for nelang in _expand_lang(lang):
                if nelang not in nelangs:
                    nelangs.append(nelang)

        # Finally, select a language
        for lang in nelangs:
            linfo_path = os.path.join('locale', lang, 'activity.linfo')
            linfo_file = self.get_file(linfo_path)
            if linfo_file is not None:
                return linfo_file
        return None

    def _parse_linfo(self, linfo_file):
        cp = ConfigParser()
        cp.readfp(linfo_file)

        section = 'Activity'

        if cp.has_option(section, 'name'):
            self._name = cp.get(section, 'name')

        if cp.has_option(section, 'summary'):
            self._summary = cp.get(section, 'summary')

        if cp.has_option(section, 'tags'):
            tag_list = cp.get(section, 'tags').strip(';')
            self._tags = [tag.strip() for tag in tag_list.split(';')]

    def get_locale_path(self):
        """Get the locale path inside the (installed) activity bundle."""
        if self._zip_file is not None:
            raise NotInstalledException
        return os.path.join(self._path, 'locale')

    def get_icons_path(self):
        """Get the icons path inside the (installed) activity bundle."""
        if self._zip_file is not None:
            raise NotInstalledException
        return os.path.join(self._path, 'icons')

    def get_name(self):
        """Get the activity user-visible name."""
        return self._name

    def get_installation_time(self):
        """Get a timestamp representing the time at which this activity was
        installed."""
        return self._installation_time

    def get_bundle_id(self):
        """Get the activity bundle id"""
        return self._bundle_id

    def get_icon(self):
        """Get the activity icon name"""
        # FIXME: this should return the icon data, not a filename, so that
        # we don't need to create a temp file in the zip case
        icon_path = os.path.join('activity', self._icon + '.svg')
        if self._zip_file is None:
            return os.path.join(self._path, icon_path)
        else:
            icon_data = self.get_file(icon_path).read()
            temp_file, temp_file_path = tempfile.mkstemp(prefix=self._icon,
                                                         suffix='.svg')
            os.write(temp_file, icon_data)
            os.close(temp_file)
            return temp_file_path

    def get_activity_version(self):
        """Get the activity version"""
        return self._activity_version

    def get_command(self):
        """Get the command to execute to launch the activity factory"""
        if self.bundle_exec:
            command = os.path.expandvars(self.bundle_exec)
        else:
            command = 'sugar-activity ' + self.activity_class

        return command

    def get_mime_types(self):
        """Get the MIME types supported by the activity"""
        return self._mime_types

    def get_tags(self):
        """Get the tags that describe the activity"""
        return self._tags

    def get_summary(self):
        """Get the summary that describe the activity"""
        return self._summary

    def get_show_launcher(self):
        """Get whether there should be a visible launcher for the activity"""
        return self._show_launcher

    def install(self):
        install_dir = env.get_user_activities_path()

        self._unzip(install_dir)

        install_path = os.path.join(install_dir, self._zip_root_dir)
        self.install_mime_type(install_path)

        return install_path

    def install_mime_type(self, install_path):
        """ Update the mime type database and install the mime type icon
        """
        xdg_data_home = os.getenv('XDG_DATA_HOME',
                                  os.path.expanduser('~/.local/share'))

        mime_path = os.path.join(install_path, 'activity', 'mimetypes.xml')
        if os.path.isfile(mime_path):
            mime_dir = os.path.join(xdg_data_home, 'mime')
            mime_pkg_dir = os.path.join(mime_dir, 'packages')
            if not os.path.isdir(mime_pkg_dir):
                os.makedirs(mime_pkg_dir)
            installed_mime_path = os.path.join(mime_pkg_dir,
                                               '%s.xml' % self._bundle_id)
            self._symlink(mime_path, installed_mime_path)
            os.spawnlp(os.P_WAIT, 'update-mime-database',
                       'update-mime-database', mime_dir)

        mime_types = self.get_mime_types()
        if mime_types is not None:
            installed_icons_dir = \
                os.path.join(xdg_data_home,
                             'icons/sugar/scalable/mimetypes')
            if not os.path.isdir(installed_icons_dir):
                os.makedirs(installed_icons_dir)

            for mime_type in mime_types:
                mime_icon_base = os.path.join(install_path, 'activity',
                                              mime_type.replace('/', '-'))
                svg_file = mime_icon_base + '.svg'
                info_file = mime_icon_base + '.icon'
                self._symlink(svg_file,
                              os.path.join(installed_icons_dir,
                                           os.path.basename(svg_file)))
                self._symlink(info_file,
                              os.path.join(installed_icons_dir,
                                           os.path.basename(info_file)))

    def _symlink(self, src, dst):
        if not os.path.isfile(src):
            return
        if not os.path.islink(dst) and os.path.exists(dst):
            raise RuntimeError('Do not remove %s if it was not '
                               'installed by sugar', dst)
        logging.debug('Link resource %s to %s', src, dst)
        if os.path.lexists(dst):
            logging.debug('Relink %s', dst)
            os.unlink(dst)
        os.symlink(src, dst)

    def uninstall(self, force=False, delete_profile=False):
        install_path = self.get_path()

        if os.path.islink(install_path):
            # Don't remove the actual activity dir if it's a symbolic link
            # because we may be removing user data.
            os.unlink(install_path)
            return

        xdg_data_home = os.getenv('XDG_DATA_HOME',
                                  os.path.expanduser('~/.local/share'))

        mime_dir = os.path.join(xdg_data_home, 'mime')
        installed_mime_path = os.path.join(mime_dir, 'packages',
                                           '%s.xml' % self._bundle_id)
        if os.path.exists(installed_mime_path):
            os.remove(installed_mime_path)
            os.spawnlp(os.P_WAIT, 'update-mime-database',
                       'update-mime-database', mime_dir)

        mime_types = self.get_mime_types()
        if mime_types is not None:
            installed_icons_dir = \
                os.path.join(xdg_data_home,
                             'icons/sugar/scalable/mimetypes')
            if os.path.isdir(installed_icons_dir):
                for f in os.listdir(installed_icons_dir):
                    path = os.path.join(installed_icons_dir, f)
                    if os.path.islink(path) and \
                       os.readlink(path).startswith(install_path):
                        os.remove(path)

        if delete_profile:
            bundle_profile_path = env.get_profile_path(self._bundle_id)
            if os.path.exists(bundle_profile_path):
                os.chmod(bundle_profile_path, 0775)
                shutil.rmtree(bundle_profile_path, ignore_errors=True)

        self._uninstall(install_path)

    def is_user_activity(self):
        return self.get_path().startswith(env.get_user_activities_path())

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
import locale
import os
import shutil
import tempfile
import logging
import warnings

from sugar import env
from sugar import util
from sugar.bundle.bundle import Bundle, \
    MalformedBundleException, NotInstalledException


class ActivityBundle(Bundle):
    """A Sugar activity bundle

    See http://wiki.laptop.org/go/Activity_bundles for details
    """

    MIME_TYPE = 'application/vnd.olpc-sugar'
    DEPRECATED_MIME_TYPE = 'application/vnd.olpc-x-sugar'

    _zipped_extension = '.xo'
    _unzipped_extension = '.activity'
    _infodir = 'activity'

    def __init__(self, path):
        Bundle.__init__(self, path)
        self.activity_class = None
        self.bundle_exec = None

        self._name = None
        self._local_name = None
        self._icon = None
        self._bundle_id = None
        self._mime_types = None
        self._show_launcher = True
        self._tags = None
        self._activity_version = 0
        self._installation_time = os.stat(path).st_mtime
        self._manifest = None

        info_file = self.get_file('activity/activity.info')
        if info_file is None:
            raise MalformedBundleException('No activity.info file')
        self._parse_info(info_file)

        linfo_file = self._get_linfo_file()
        if linfo_file:
            self._parse_linfo(linfo_file)

        if self._local_name == None:
            self._local_name = self._name

    def _get_manifest(self):
        if self._manifest is None:
            self._manifest = self._read_manifest()
        return self._manifest

    manifest = property(_get_manifest, None, None,
        "NOTICE: this property is potentially quite slow, so better make sure "
        "that it's not called at performance-critical points like shell or "
        "activity startup.")

    def _raw_manifest(self):
        f = self.get_file("MANIFEST")
        if not f:
            logging.warning("Activity directory lacks a MANIFEST file.")
            return []

        ret = [line.strip() for line in f.readlines()]
        f.close()
        return ret

    def _read_manifest(self):
        """return a list with the lines in MANIFEST, with invalid lines
        replaced by empty lines.

        Since absolute order carries information on file history, it should
        be preserved. For instance, when renaming a file, you should leave
        the new name on the same line as the old one.
        """
        logging.debug('STARTUP: Reading manifest')
        lines = self._raw_manifest()

        # Remove trailing newlines, they do not help keep absolute position.
        while lines and lines[-1] == "":
            lines = lines[:-1]

        for num, line in enumerate(lines):
            if not line:
                continue

            # Remove duplicates
            if line in lines[0:num]:
                lines[num] = ""
                logging.warning('Bundle %s: duplicate entry in MANIFEST: %s',
                    self._name, line)
                continue

            # Remove MANIFEST
            if line == "MANIFEST":
                lines[num] = ""
                logging.warning('Bundle %s: MANIFEST includes itself: %s',
                    self._name, line)

            # Remove invalid files
            if not self.is_file(line):
                lines[num] = ""
                logging.warning('Bundle %s: invalid entry in MANIFEST: %s',
                    self._name, line)

        return lines

    def get_files(self, manifest = None):
        files = [line for line in (manifest or self.manifest) if line]

        if self.is_file('MANIFEST'):
            files.append('MANIFEST')

        return files

    def _parse_info(self, info_file):
        cp = ConfigParser()
        cp.readfp(info_file)

        section = 'Activity'

        if cp.has_option(section, 'bundle_id'):
            self._bundle_id = cp.get(section, 'bundle_id')
        # FIXME deprecated
        elif cp.has_option(section, 'service_name'):
            warnings.warn('use bundle_id instead of service_name ' \
                              'in your activity.info', DeprecationWarning)
            self._bundle_id = cp.get(section, 'service_name')
        else:
            raise MalformedBundleException(
                'Activity bundle %s does not specify a bundle id' %
                self._path)

        if cp.has_option(section, 'name'):
            self._name = cp.get(section, 'name')
        else:
            raise MalformedBundleException(
                'Activity bundle %s does not specify a name' % self._path)

        # FIXME class is deprecated
        if cp.has_option(section, 'class'):
            warnings.warn('use exec instead of class ' \
                              'in your activity.info', DeprecationWarning)
            self.activity_class = cp.get(section, 'class')
        elif cp.has_option(section, 'exec'):
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
                self._activity_version = int(version)
            except ValueError:
                raise MalformedBundleException(
                    'Activity bundle %s has invalid version number %s' %
                    (self._path, version))

    def _get_linfo_file(self):
        lang = locale.getdefaultlocale()[0]
        if not lang:
            return None

        linfo_path = os.path.join('locale', lang, 'activity.linfo')
        linfo_file = self.get_file(linfo_path)
        if linfo_file is not None:
            return linfo_file

        linfo_path = os.path.join('locale', lang[:2], 'activity.linfo')
        linfo_file = self.get_file(linfo_path)
        if linfo_file is not None:
            return linfo_file

        return None

    def _parse_linfo(self, linfo_file):
        cp = ConfigParser()
        cp.readfp(linfo_file)

        section = 'Activity'

        if cp.has_option(section, 'name'):
            self._local_name = cp.get(section, 'name')

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

    def get_path(self):
        """Get the activity bundle path."""
        return self._path

    def get_name(self):
        """Get the activity user-visible name."""
        return self._local_name

    def get_bundle_name(self):
        """Get the activity bundle name."""
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
            return util.TempFilePath(temp_file_path)

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

    def get_show_launcher(self):
        """Get whether there should be a visible launcher for the activity"""
        return self._show_launcher

    def install(self, install_dir=None, strict_manifest=False):
        if install_dir is None:
            install_dir = env.get_user_activities_path()

        self._unzip(install_dir)

        install_path = os.path.join(install_dir, self._zip_root_dir)

        # List installed files
        manifestfiles = self.get_files(self._raw_manifest())
        paths = []
        for root, dirs_, files in os.walk(install_path):
            rel_path = root[len(install_path) + 1:]
            for f in files:
                paths.append(os.path.join(rel_path, f))

        # Check the list against the MANIFEST
        for path in paths:
            if path in manifestfiles:
                manifestfiles.remove(path)
            elif path != "MANIFEST":
                logging.warning('Bundle %s: %s not in MANIFEST', self._name,
                    path)
                if strict_manifest:
                    os.remove(os.path.join(install_path, path))

        # Is anything in MANIFEST left over after accounting for all files?
        if manifestfiles:
            err = ("Bundle %s: files in MANIFEST not included: %s"%
                   (self._name, str(manifestfiles)))
            if strict_manifest:
                raise MalformedBundleException(err)
            else:
                logging.warning(err)

        self.install_mime_type(install_path)

        return install_path

    def install_mime_type(self, install_path):
        ''' Update the mime type database and install the mime type icon
        '''
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
            installed_icons_dir = os.path.join(xdg_data_home,
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

    def uninstall(self, install_path, force=False, delete_profile=False):
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
            installed_icons_dir = os.path.join(xdg_data_home,
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

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

"""Sugar activity bundles"""

from ConfigParser import ConfigParser
import locale
import os
import tempfile

from sugar.bundle.bundle import Bundle, MalformedBundleException, \
    AlreadyInstalledException, RegistrationException, \
    NotInstalledException

from sugar import activity
from sugar import env

import logging

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
        self._icon = None
        self._bundle_id = None
        self._mime_types = None
        self._show_launcher = True
        self._activity_version = 0

        info_file = self.get_file('activity/activity.info')
        if info_file is None:
            raise MalformedBundleException('No activity.info file')
        self._parse_info(info_file)

        linfo_file = self._get_linfo_file()
        if linfo_file:
            self._parse_linfo(linfo_file)

        self.manifest = None #This should be replaced by following function
        self.read_manifest()

    def _raw_manifest(self):
        f = self.get_file("MANIFEST")
        if not f:
            logging.warning("Activity directory lacks a MANIFEST file.")
            return []
        
        ret = [line.strip() for line in f.readlines()] 
        f.close()
        return ret
        
    def read_manifest(self):
        """read_manifest: sets self.manifest to list of lines in MANIFEST, 
        with invalid lines replaced by empty lines.
        
        Since absolute order carries information on file history, it should 
        be preserved. For instance, when renaming a file, you should leave
        the new name on the same line as the old one.
        """
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
                logging.warning("Bundle %s: duplicate entry in MANIFEST: %s"
                                % (self._name,line))
                continue
            
            # Remove MANIFEST
            if line == "MANIFEST":
                lines[num] = ""
                logging.warning("Bundle %s: MANIFEST includes itself: %s"
                                % (self._name,line))
                
            # Remove invalid files
            if not self.is_file(line):
                lines[num] = ""
                logging.warning("Bundle %s: invalid entry in MANIFEST: %s"
                                % (self._name,line))

        self.manifest = lines
    
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
            self.activity_class = cp.get(section, 'class')
        elif cp.has_option(section, 'exec'):
            self.bundle_exec = cp.get(section, 'exec')
        else:
            raise MalformedBundleException(
                'Activity bundle %s must specify either class or exec' %
                self._path)

        if cp.has_option(section, 'mime_types'):
            mime_list = cp.get(section, 'mime_types').strip(';')
            self._mime_types = [ mime.strip() for mime in mime_list.split(';') ]

        if cp.has_option(section, 'show_launcher'):
            if cp.get(section, 'show_launcher') == 'no':
                self._show_launcher = False

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
            self._name = cp.get(section, 'name')

    def get_locale_path(self):
        """Get the locale path inside the (installed) activity bundle."""
        if not self._unpacked:
            raise NotInstalledException
        return os.path.join(self._path, 'locale')

    def get_icons_path(self):
        """Get the icons path inside the (installed) activity bundle."""
        if not self._unpacked:
            raise NotInstalledException
        return os.path.join(self._path, 'icons')

    def get_path(self):
        """Get the activity bundle path."""
        return self._path

    def get_name(self):
        """Get the activity user visible name."""
        return self._name

    def get_installation_time(self):
        """Get a timestamp representing the time at which this activity was
        installed."""
        return os.stat(self._path).st_mtime

    def get_bundle_id(self):
        """Get the activity bundle id"""
        return self._bundle_id

    # FIXME: this should return the icon data, not a filename, so that
    # we don't need to create a temp file in the zip case
    def get_icon(self):
        """Get the activity icon name"""
        icon_path = os.path.join('activity', self._icon + '.svg')
        if self._unpacked:
            return os.path.join(self._path, icon_path)
        else:
            icon_data = self.get_file(icon_path).read()
            temp_file, temp_file_path = tempfile.mkstemp(self._icon)
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

    def get_show_launcher(self):
        """Get whether there should be a visible launcher for the activity"""
        return self._show_launcher

    def is_installed(self):
        if activity.get_registry().get_activity(self._bundle_id):
            return True
        else:
            return False

    def need_upgrade(self):
        act = activity.get_registry().get_activity(self._bundle_id)
        if act is None or act.version != self._activity_version:
            return True
        else:
            return False
    
    def unpack(self, install_dir, strict_manifest=False):
        self._unzip(install_dir)

        install_path = os.path.join(install_dir, self._zip_root_dir)
        
        # List installed files
        manifestfiles = self.get_files(self._raw_manifest())
        paths  = []
        for root, dirs, files in os.walk(install_path):
            rel_path = root[len(install_path) + 1:]
            for f in files:
                paths.append(os.path.join(rel_path, f))
                
        # Check the list against the MANIFEST
        for path in paths:
            if path in manifestfiles:
                manifestfiles.remove(path)
            elif path != "MANIFEST":
                logging.warning("Bundle %s: %s not in MANIFEST"%
                                (self._name,path))
                if strict_manifest:
                    os.remove(os.path.join(install_path, path))
                    
        # Is anything in MANIFEST left over after accounting for all files?
        if manifestfiles:
            err = ("Bundle %s: files in MANIFEST not included: %s"%
                   (self._name,str(manifestfiles)))
            if strict_manifest:
                raise MalformedBundleException(err)
            else:
                logging.warning(err)

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
            os.symlink(mime_path, installed_mime_path)
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
                if os.path.isfile(svg_file):
                    os.symlink(svg_file,
                               os.path.join(installed_icons_dir,
                                            os.path.basename(svg_file)))
                if os.path.isfile(info_file):
                    os.symlink(info_file,
                               os.path.join(installed_icons_dir,
                                            os.path.basename(info_file)))
        return install_path

    def install(self):
        activities_path = env.get_user_activities_path()
        act = activity.get_registry().get_activity(self._bundle_id)
        if act is not None and act.path.startswith(activities_path):
            raise AlreadyInstalledException

        install_dir = env.get_user_activities_path()
        install_path = self.unpack(install_dir)
        
        if not activity.get_registry().add_bundle(install_path):
            raise RegistrationException

    def uninstall(self, force=False):        
        if self._unpacked:
            install_path = self._path
        else:
            if not self.is_installed():
                raise NotInstalledException

            act = activity.get_registry().get_activity(self._bundle_id)
            if not force and act.version != self._activity_version:
                logging.warning('Not uninstalling, different bundle present')
                return
            elif not act.path.startswith(env.get_user_activities_path()):
                logging.warning('Not uninstalling system activity')
                return

            install_path = os.path.join(env.get_user_activities_path(),
                                        self._zip_root_dir)

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
            for f in os.listdir(installed_icons_dir):
                path = os.path.join(installed_icons_dir, f)
                if os.path.islink(path) and \
                   os.readlink(path).startswith(install_path):
                    os.remove(path)

        self._uninstall(install_path)
        
        if not activity.get_registry().remove_bundle(install_path):
            raise RegistrationException

    def upgrade(self):
        act = activity.get_registry().get_activity(self._bundle_id)
        if act is None:
            logging.warning('Activity not installed')
        elif act.path.startswith(env.get_user_activities_path()):
            try:
                self.uninstall(force=True)
            except Exception, e:
                logging.warning('Uninstall failed (%s), still trying ' \
                                'to install newer bundle', e)
        else:
            logging.warning('Unable to uninstall system activity, ' \
                            'installing upgraded version in user activities')

        self.install()


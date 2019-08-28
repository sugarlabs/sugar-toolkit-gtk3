# Copyright (C) 2008 Red Hat, Inc.
# Copyright (C) 2016 Sam Parkinson <sam@sam.today>
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

'''
The bundle builder is a build system for Sugar activities.  Usually, it
is setup by creating a `setup.py` file in the project with the following::

    #!/usr/bin/env python

    from sugar3.activity import bundlebuilder
    bundlebuilder.start()
'''

import argparse
import operator
import os
import sys
import zipfile
import tarfile
import unittest
import shutil
import subprocess
import re
import gettext
import logging
from glob import glob
from fnmatch import fnmatch
from six.moves.configparser import ConfigParser
import xml.etree.cElementTree as ET
from six.moves.html_parser import HTMLParser

from sugar3 import env
from sugar3.bundle.activitybundle import ActivityBundle
from six.moves import reduce


IGNORE_DIRS = ['dist', '.git', 'screenshots']
IGNORE_FILES = ['.gitignore', 'MANIFEST', '*.pyc', '*~', '*.bak', 'pseudo.po']


def list_files(base_dir, ignore_dirs=None, ignore_files=None):
    result = []

    base_dir = os.path.abspath(base_dir)

    for root, dirs, files in os.walk(base_dir):
        if ignore_files:
            for pattern in ignore_files:
                files = [f for f in files if not fnmatch(f, pattern)]

        rel_path = root[len(base_dir) + 1:]
        for f in files:
            result.append(os.path.join(rel_path, f))

        if ignore_dirs and root == base_dir:
            for ignore in ignore_dirs:
                if ignore in dirs:
                    dirs.remove(ignore)

    return result


class Config(object):

    def __init__(self, source_dir, dist_dir=None, dist_name=None):
        self.source_dir = source_dir
        self.build_dir = os.getcwd()
        self.dist_dir = dist_dir or os.path.join(self.build_dir, 'dist')
        self.dist_name = dist_name
        self.bundle = None
        self.version = None
        self.activity_name = None
        self.bundle_id = None
        self.bundle_name = None
        self.bundle_root_dir = None
        self.tar_root_dir = None
        self.xo_name = None
        self.tar_name = None
        self.summary = None
        self.description = None

        self.update()

    def update(self):
        self.bundle = bundle = ActivityBundle(self.source_dir,
                                              translated=False)
        self.version = bundle.get_activity_version()
        self.activity_name = bundle.get_name()
        self.bundle_id = bundle.get_bundle_id()
        self.summary = bundle.get_summary()
        self.description = bundle.get_description()
        self.bundle_name = reduce(operator.add, self.activity_name.split())
        self.bundle_root_dir = self.bundle_name + '.activity'
        self.tar_root_dir = '%s-%s' % (self.bundle_name, self.version)
        if self.dist_name:
            self.xo_name = '%s.xo' % self.dist_name
            self.tar_name = '%s.tar.bz2' % self.dist_name
        else:
            self.xo_name = '%s-%s.xo' % (self.bundle_name, self.version)
            self.tar_name = '%s-%s.tar.bz2' % (self.bundle_name, self.version)


class Builder(object):

    def __init__(self, config, no_fail=False):
        self.config = config
        self._no_fail = no_fail
        self.locale_dir = os.path.join(self.config.build_dir, 'locale')

    def build(self):
        self.build_locale()

    def build_locale(self):
        po_dir = os.path.join(self.config.source_dir, 'po')

        if not self.config.bundle.is_dir(po_dir):
            logging.warn('Missing po/ dir, cannot build_locale')
            return

        if os.path.exists(self.locale_dir):
            shutil.rmtree(self.locale_dir)

        for f in sorted(os.listdir(po_dir)):
            if not f.endswith('.po') or f == 'pseudo.po':
                continue

            file_name = os.path.join(po_dir, f)
            lang = f[:-3]

            localedir = os.path.join(self.config.build_dir, 'locale', lang)
            mo_path = os.path.join(localedir, 'LC_MESSAGES')
            if not os.path.isdir(mo_path):
                os.makedirs(mo_path)

            mo_file = os.path.join(mo_path, '%s.mo' % self.config.bundle_id)
            args = ['msgfmt', '--output-file=%s' % mo_file, file_name]
            retcode = subprocess.call(args)
            if retcode:
                print('ERROR - msgfmt failed with return code %i.' % retcode)
                if self._no_fail:
                    continue

            cat = gettext.GNUTranslations(open(mo_file, 'rb'))
            translated_name = cat.gettext(self.config.activity_name)
            translated_summary = cat.gettext(self.config.summary)
            if translated_summary is None:
                translated_summary = ''
            if translated_summary.find('\n') > -1:
                translated_summary = translated_summary.replace('\n', '')
                logging.warn(
                    'Translation of summary on file %s have \\n chars. '
                    'Should be removed' % file_name)
            linfo_file = os.path.join(localedir, 'activity.linfo')
            f = open(linfo_file, 'w')
            f.write('[Activity]\nname = %s\n' % translated_name)
            f.write('summary = %s\n' % translated_summary)
            f.close()

    def get_locale_files(self):
        return list_files(self.locale_dir, IGNORE_DIRS, IGNORE_FILES)


class Packager(object):

    def __init__(self, config):
        self.config = config
        self.package_path = None

        if not os.path.exists(self.config.dist_dir):
            os.mkdir(self.config.dist_dir)

    def get_files_in_git(self, root=None):
        if root is None:
            root = self.config.source_dir

        git_ls = None
        try:
            git_ls = subprocess.Popen(['git', 'ls-files'],
                                      stdout=subprocess.PIPE,
                                      cwd=root)
        except OSError:
            logging.warn('Packager: git is not installed, '
                         'fall back to filtered list')

        if git_ls is not None:
            stdout, _ = git_ls.communicate()
            if git_ls.returncode:
                # Fall back to filtered list
                logging.warn('Packager: this is not a git repository, '
                             'fall back to filtered list')
            elif stdout:
                # pylint: disable=E1103
                git_output = [path.strip() for path in
                              stdout.decode().strip('\n').split('\n')]
                files = []
                for line in git_output:
                    ignore = False
                    for directory in IGNORE_DIRS:
                        if line.startswith(directory + '/'):
                            ignore = True
                            break
                    if not ignore:
                        sub_path = os.path.join(root, line)
                        if os.path.isdir(sub_path) \
                           and os.path.exists(os.path.join(sub_path, '.git')):
                            sub_list = self.get_files_in_git(sub_path)
                            for f in sub_list:
                                files.append(os.path.join(line, f))
                        else:
                            files.append(line)

                for pattern in IGNORE_FILES:
                    files = [f for f in files if not fnmatch(f, pattern)]

                return files

        return list_files(self.config.source_dir,
                          IGNORE_DIRS, IGNORE_FILES)


class XOPackager(Packager):

    def __init__(self, builder):
        Packager.__init__(self, builder.config)

        self.builder = builder
        self.builder.build_locale()
        self.package_path = os.path.join(self.config.dist_dir,
                                         self.config.xo_name)

    def package(self):
        bundle_zip = zipfile.ZipFile(self.package_path, 'w',
                                     zipfile.ZIP_DEFLATED)

        for f in self.get_files_in_git():
            bundle_zip.write(os.path.join(self.config.source_dir, f),
                             os.path.join(self.config.bundle_root_dir, f))

        for f in self.builder.get_locale_files():
            bundle_zip.write(os.path.join(self.builder.locale_dir, f),
                             os.path.join(self.config.bundle_root_dir,
                                          'locale', f))

        bundle_zip.close()


class SourcePackager(Packager):

    def __init__(self, config):
        Packager.__init__(self, config)
        self.package_path = os.path.join(self.config.dist_dir,
                                         self.config.tar_name)

    def package(self):
        tar = tarfile.open(self.package_path, 'w:bz2')
        for f in self.get_files_in_git():
            tar.add(os.path.join(self.config.source_dir, f),
                    os.path.join(self.config.tar_root_dir, f))
        tar.close()


class Installer(Packager):
    def __init__(self, builder):
        Packager.__init__(self, builder.config)
        self.builder = builder

    def install(self, prefix, install_mime=True, install_desktop_file=True):
        self.builder.build()

        activity_path = os.path.join(prefix, 'share', 'sugar', 'activities',
                                     self.config.bundle_root_dir)

        source_to_dest = {}

        for f in self.get_files_in_git():
            source_path = os.path.join(self.config.source_dir, f)
            dest_path = os.path.join(activity_path, f)
            source_to_dest[source_path] = dest_path

        for f in self.builder.get_locale_files():
            source_path = os.path.join(self.builder.locale_dir, f)

            if source_path.endswith(".mo"):
                dest_path = os.path.join(prefix, 'share', 'locale', f)
            else:
                dest_path = os.path.join(activity_path, 'locale', f)

            source_to_dest[source_path] = dest_path

        for source, dest in list(source_to_dest.items()):
            print('Install %s to %s.' % (source, dest))

            path = os.path.dirname(dest)
            if not os.path.exists(path):
                os.makedirs(path)

            shutil.copy(source, dest)

        if install_mime:
            self.config.bundle.install_mime_type(self.config.source_dir)

        if install_desktop_file:
            self._install_desktop_file(prefix, activity_path)
            self._generate_appdata(prefix, activity_path)

    def _install_desktop_file(self, prefix, activity_path):
        cp = ConfigParser()
        section = 'Desktop Entry'
        cp.add_section(section)
        cp.optionxform = str  # Allow CamelCase entries

        # Get it from the activity.info for the non-translated version
        info = ConfigParser()
        info.read(os.path.join(activity_path, 'activity', 'activity.info'))
        cp.set(section, 'Name', info.get('Activity', 'name'))
        if info.has_option('Activity', 'summary'):
            cp.set(section, 'Comment', info.get('Activity', 'summary'))

        for path in sorted(glob(os.path.join(activity_path, 'locale',
                                             '*', 'activity.linfo'))):
            locale = path.split(os.path.sep)[-2]
            info = ConfigParser()
            info.read(path)
            if info.has_option('Activity', 'name'):
                cp.set(section, 'Name[{}]'.format(locale),
                       info.get('Activity', 'name'))
            if info.has_option('Activity', 'summary'):
                cp.set(section, 'Comment[{}]'.format(locale),
                       info.get('Activity', 'summary'))

        cp.set(section, 'Terminal', 'false')
        cp.set(section, 'Type', 'Application')
        cp.set(section, 'Categories', 'Education;')
        cp.set(section, 'Icon', os.path.join(
            activity_path, 'activity', self.config.bundle.get_icon_filename()))
        cp.set(section, 'Exec', self.config.bundle.get_command())
        cp.set(section, 'Path', activity_path)  # Path == CWD for running

        name = '{}.activity.desktop'.format(self.config.bundle_id)
        path = os.path.join(prefix, 'share', 'applications', name)
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with open(path, 'w') as f:
            cp.write(f)

    def _generate_appdata(self, prefix, activity_path):
        info = ConfigParser()
        info.read(os.path.join(activity_path, 'activity', 'activity.info'))

        required_fields = ['metadata_license', 'license', 'name', 'icon',
                           'description']
        for name in required_fields:
            if not info.has_option('Activity', name):
                print('[WARNING] missing AppStream metadata, '
                      'see `pydoc sugar3.bundle`')
                return

        # See https://www.freedesktop.org/software/appstream/docs/
        root = ET.Element('component', type='desktop')
        ET.SubElement(root, 'project_group').text = 'Sugar'
        ET.SubElement(root, 'translation', type='gettext').text = \
            self.config.bundle_id
        ET.SubElement(root, 'id').text = \
            self.config.bundle_id + '.activity.desktop'
        desc = ET.fromstring('<description>{}</description>'.format(
            info.get('Activity', 'description')))
        root.append(desc)

        copy_pairs = [('metadata_license', 'metadata_license'),
                      ('license', 'project_license'),
                      ('summary', 'summary'),
                      ('name', 'name')]
        for key, ename in copy_pairs:
            ET.SubElement(root, ename).text = info.get('Activity', key)

        if info.has_option('Activity', 'screenshots'):
            screenshots = info.get('Activity', 'screenshots').split()
            ss_root = ET.SubElement(root, 'screenshots')
            for i, screenshot in enumerate(screenshots):
                e = ET.SubElement(ss_root, 'screenshot')
                if i == 0:
                    e.set('type', 'default')
                ET.SubElement(e, 'image').text = screenshot

        if info.has_option('Activity', 'url'):
            ET.SubElement(root, 'url', type='homepage').text = \
                info.get('Activity', 'url')
        if info.has_option('Activity', 'repository_url'):
            ET.SubElement(root, 'url', type='bugtracker').text = \
                info.get('Activity', 'repository_url')
        elif info.has_option('Activity', 'repository'):
            ET.SubElement(root, 'url', type='bugtracker').text = \
                info.get('Activity', 'repository')

        path = os.path.join(prefix, 'share', 'metainfo',
                            self.config.bundle_id + '.appdata.xml')
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        tree = ET.ElementTree(root)
        tree.write(path, encoding='UTF-8')


def cmd_check(config, options):
    """Run tests for the activity"""

    run_unit_test = True
    run_integration_test = True

    if options.choice == 'unit':
        run_integration_test = False
    if options.choice == 'integration':
        run_unit_test = False

    print("Running Tests")

    test_path = os.path.join(config.source_dir, "tests")

    if os.path.isdir(test_path):
        unit_test_path = os.path.join(test_path, "unit")
        integration_test_path = os.path.join(test_path, "integration")
        sys.path.append(config.source_dir)

        # Run Tests
        if os.path.isdir(unit_test_path) and run_unit_test:
            all_tests = unittest.defaultTestLoader.discover(unit_test_path)
            unittest.TextTestRunner(verbosity=options.verbose).run(all_tests)
        elif not run_unit_test:
            print("Not running unit tests")
        else:
            print('No "unit" directory found.')

        if os.path.isdir(integration_test_path) and run_integration_test:
            all_tests = unittest.defaultTestLoader.discover(
                integration_test_path)
            unittest.TextTestRunner(verbosity=options.verbose).run(all_tests)
        elif not run_integration_test:
            print("Not running integration tests")
        else:
            print('No "integration" directory found.')

        print("Finished testing")
    else:
        print("Error: No tests/ directory")


def cmd_dev(config, options):
    """Setup for development"""

    bundle_path = env.get_user_activities_path()
    if not os.path.isdir(bundle_path):
        os.mkdir(bundle_path)
    bundle_path = os.path.join(bundle_path, config.bundle_root_dir)
    try:
        os.symlink(config.source_dir, bundle_path)
    except OSError:
        if os.path.islink(bundle_path):
            print('ERROR - The bundle has been already setup for development.')
        else:
            print('ERROR - A bundle with the same name is already installed.')


def cmd_dist_xo(config, options):
    """Create a xo bundle package"""
    no_fail = False
    if options is not None:
        no_fail = options.no_fail

    packager = XOPackager(Builder(config, no_fail))
    packager.package()


def cmd_fix_manifest(config, options):
    '''Add missing files to the manifest (OBSOLETE)'''

    print('WARNING: The fix_manifest command is obsolete.')
    print('         The MANIFEST file is no longer used in bundles,')
    print('         please remove it.')


def cmd_dist_source(config, options):
    """Create a tar source package"""

    packager = SourcePackager(config)
    packager.package()


def cmd_install(config, options):
    """Install the activity in the system"""

    installer = Installer(Builder(config))
    installer.install(
        options.prefix,
        options.install_mime,
        options.install_desktop_file)


def _po_escape(string):
    return re.sub('([\\\\"])', '\\\\\\1', string)


def cmd_genpot(config, options):
    """Generate the gettext pot file"""

    os.chdir(config.source_dir)

    po_path = os.path.join(config.source_dir, 'po')
    if not os.path.isdir(po_path):
        os.mkdir(po_path)

    python_files = []
    for root, dirs_dummy, files in os.walk(config.source_dir):
        for file_name in files:
            if file_name.endswith('.py'):
                file_path = os.path.relpath(os.path.join(root, file_name),
                                            config.source_dir)
                python_files.append(file_path)
    python_files.sort()

    # First write out a stub .pot file containing just the translated
    # activity name, then have xgettext merge the rest of the
    # translations into that. (We can't just append the activity name
    # to the end of the .pot file afterwards, because that might
    # create a duplicate msgid.)
    pot_file = os.path.join('po', '%s.pot' % config.bundle_name)
    escaped_name = _po_escape(config.activity_name)
    f = open(pot_file, 'w')
    f.write('#: activity/activity.info:2\n')
    f.write('msgid "%s"\n' % escaped_name)
    f.write('msgstr ""\n')
    if config.summary is not None:
        escaped_summary = _po_escape(config.summary)
        f.write('#: activity/activity.info:3\n')
        f.write('msgid "%s"\n' % escaped_summary)
        f.write('msgstr ""\n')

    if config.description is not None:
        parser = HTMLParser()
        strings = []
        parser.handle_data = strings.append
        parser.feed(config.description)

        for s in strings:
            s = s.strip()
            if s:
                f.write('#: activity/activity.info:4\n')
                f.write('msgid "%s"\n' % _po_escape(s))
                f.write('msgstr ""\n')
    f.close()

    args = ['xgettext', '--join-existing', '--language=Python',
            '--keyword=_', '--add-comments=TRANS:', '--output=%s' % pot_file]

    args += python_files
    retcode = subprocess.call(args)
    if retcode:
        print('ERROR - xgettext failed with return code %i.' % retcode)


def cmd_build(config, options):
    """Build generated files"""

    builder = Builder(config)
    builder.build()


def start():
    parser = argparse.ArgumentParser(prog='./setup.py')
    subparsers = parser.add_subparsers(
        dest="command", help="Options for %(prog)s")

    install_parser = subparsers.add_parser(
        "install", help="Install the activity in the system")
    install_parser.add_argument(
        "--prefix", dest="prefix", default=sys.prefix,
        help="Path for installing")
    install_parser.add_argument(
        "--skip-install-mime", dest="install_mime",
        action="store_false", default=True,
        help="Skip the installation of custom mime types in the system")
    install_parser.add_argument(
        "--skip-install-desktop-file", dest="install_desktop_file",
        action="store_false", default=True,
        help="Skip the installation of desktop file in the system")

    check_parser = subparsers.add_parser(
        "check", help="Run tests for the activity")
    check_parser.add_argument("choice", nargs='?',
                              choices=['unit', 'integration'],
                              help="run unit/integration test")
    check_parser.add_argument("--verbosity", "-v", dest="verbose",
                              type=int, choices=list(range(0, 3)),
                              default=1, nargs='?',
                              help="verbosity for the unit tests")

    dist_parser = subparsers.add_parser("dist_xo",
                                        help="Create a xo bundle package")
    dist_parser.add_argument(
        "--no-fail", dest="no_fail", action="store_true", default=False,
        help="continue past failure when building xo file")

    subparsers.add_parser("dist_source", help="Create a tar source package")
    subparsers.add_parser("build", help="Build generated files")
    subparsers.add_parser(
        "fix_manifest", help="Add missing files to the manifest (OBSOLETE)")
    subparsers.add_parser("genpot", help="Generate the gettext pot file")
    subparsers.add_parser("dev", help="Setup for development")

    options = parser.parse_args()

    source_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
    config = Config(source_dir)

    try:
        globals()['cmd_' + options.command](config, options)
    except (KeyError, IndexError):
        parser.print_help()


if __name__ == '__main__':
    start()

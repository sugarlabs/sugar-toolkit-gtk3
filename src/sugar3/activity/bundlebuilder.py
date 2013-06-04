# Copyright (C) 2008 Red Hat, Inc.
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

"""
STABLE.
"""

import operator
import os
import sys
import zipfile
import tarfile
import shutil
import subprocess
import re
import gettext
from optparse import OptionParser
import logging
from fnmatch import fnmatch

from sugar3 import env
from sugar3.bundle.activitybundle import ActivityBundle


IGNORE_DIRS = ['dist', '.git']
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

    def __init__(self, source_dir):
        self.source_dir = source_dir
        self.build_dir = os.getcwd()
        self.dist_dir = os.path.join(self.build_dir, 'dist')
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

        self.update()

    def update(self):
        self.bundle = bundle = ActivityBundle(self.source_dir,
                                              translated=False)
        self.version = bundle.get_activity_version()
        self.activity_name = bundle.get_name()
        self.bundle_id = bundle.get_bundle_id()
        self.summary = bundle.get_summary()
        self.bundle_name = reduce(operator.add, self.activity_name.split())
        self.bundle_root_dir = self.bundle_name + '.activity'
        self.tar_root_dir = '%s-%s' % (self.bundle_name, self.version)
        self.xo_name = '%s-%s.xo' % (self.bundle_name, self.version)
        self.tar_name = '%s-%s.tar.bz2' % (self.bundle_name, self.version)


class Builder(object):

    def __init__(self, config):
        self.config = config
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

        for f in os.listdir(po_dir):
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
                print 'ERROR - msgfmt failed with return code %i.' % retcode

            cat = gettext.GNUTranslations(open(mo_file, 'r'))
            translated_name = cat.gettext(self.config.activity_name)
            translated_summary = cat.gettext(self.config.summary)
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

    def get_files_in_git(self):
        try:
            git_ls = subprocess.Popen(['git', 'ls-files'],
                                      stdout=subprocess.PIPE,
                                      cwd=self.config.source_dir)
        except OSError:
            logging.warn('Packager: git is not installed, ' \
                             'fall back to filtered list')
            return list_files(self.config.source_dir,
                              IGNORE_DIRS, IGNORE_FILES)

        stdout, _ = git_ls.communicate()
        if git_ls.returncode:
            # Fall back to filtered list
            logging.warn('Packager: this is not a git repository, ' \
                             'fall back to filtered list')
            return list_files(self.config.source_dir,
                              IGNORE_DIRS, IGNORE_FILES)

        # pylint: disable=E1103
        return [path.strip() for path in stdout.strip('\n').split('\n')]


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

    def install(self, prefix):
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

        for source, dest in source_to_dest.items():
            print 'Install %s to %s.' % (source, dest)

            path = os.path.dirname(dest)
            if not os.path.exists(path):
                os.makedirs(path)

            shutil.copy(source, dest)

        self.config.bundle.install_mime_type(self.config.source_dir)


def cmd_dev(config, args):
    """Setup for development"""

    if args:
        print 'Usage: %prog dev'
        return

    bundle_path = env.get_user_activities_path()
    if not os.path.isdir(bundle_path):
        os.mkdir(bundle_path)
    bundle_path = os.path.join(bundle_path, config.bundle_root_dir)
    try:
        os.symlink(config.source_dir, bundle_path)
    except OSError:
        if os.path.islink(bundle_path):
            print 'ERROR - The bundle has been already setup for development.'
        else:
            print 'ERROR - A bundle with the same name is already installed.'


def cmd_dist_xo(config, args):
    """Create a xo bundle package"""

    if args:
        print 'Usage: %prog dist_xo'
        return

    packager = XOPackager(Builder(config))
    packager.package()


def cmd_fix_manifest(config, args):
    '''Add missing files to the manifest (OBSOLETE)'''

    print 'WARNING: The fix_manifest command is obsolete.'
    print '         The MANIFEST file is no longer used in bundles,'
    print '         please remove it.'


def cmd_dist_source(config, args):
    """Create a tar source package"""

    if args:
        print 'Usage: %prog dist_source'
        return

    packager = SourcePackager(config)
    packager.package()


def cmd_install(config, args):
    """Install the activity in the system"""

    parser = OptionParser(usage='usage: %prog install [options]')
    parser.add_option('--prefix', dest='prefix', default=sys.prefix,
                      help='Prefix to install files to')
    (suboptions, subargs) = parser.parse_args(args)
    if subargs:
        parser.print_help()
        return

    installer = Installer(Builder(config))
    installer.install(suboptions.prefix)


def cmd_genpot(config, args):
    """Generate the gettext pot file"""

    if args:
        print 'Usage: %prog genpot'
        return

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

    # First write out a stub .pot file containing just the translated
    # activity name, then have xgettext merge the rest of the
    # translations into that. (We can't just append the activity name
    # to the end of the .pot file afterwards, because that might
    # create a duplicate msgid.)
    pot_file = os.path.join('po', '%s.pot' % config.bundle_name)
    escaped_name = re.sub('([\\\\"])', '\\\\\\1', config.activity_name)
    f = open(pot_file, 'w')
    f.write('#: activity/activity.info:2\n')
    f.write('msgid "%s"\n' % escaped_name)
    f.write('msgstr ""\n')
    if config.summary is not None:
        escaped_summary = re.sub('([\\\\"])', '\\\\\\1', config.summary)
        f.write('#: activity/activity.info:3\n')
        f.write('msgid "%s"\n' % escaped_summary)
        f.write('msgstr ""\n')
    f.close()

    args = ['xgettext', '--join-existing', '--language=Python',
        '--keyword=_', '--add-comments=TRANS:', '--output=%s' % pot_file]

    args += python_files
    retcode = subprocess.call(args)
    if retcode:
        print 'ERROR - xgettext failed with return code %i.' % retcode


def cmd_build(config, args):
    """Build generated files"""

    if args:
        print 'Usage: %prog build'
        return

    builder = Builder(config)
    builder.build()


def print_commands():
    print 'Available commands:\n'

    for name, func in globals().items():
        if name.startswith('cmd_'):
            print '%-20s %s' % (name.replace('cmd_', ''), func.__doc__)

    print '\n(Type "./setup.py <command> --help" for help about a ' \
          'particular command\'s options.'


def start():
    parser = OptionParser(usage='[action] [options]')
    parser.disable_interspersed_args()
    (options_, args) = parser.parse_args()

    source_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
    config = Config(source_dir)

    try:
        globals()['cmd_' + args[0]](config, args[1:])
    except (KeyError, IndexError):
        print_commands()


if __name__ == '__main__':
    start()

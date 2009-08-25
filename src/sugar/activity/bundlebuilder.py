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

from sugar import env
from sugar.bundle.activitybundle import ActivityBundle


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

    def __init__(self, source_dir=None, dist_dir = None, dist_name = None):
        self.source_dir = source_dir or os.getcwd()
        self.dist_dir = dist_dir or os.path.join(self.source_dir, 'dist')
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

        self.update()

    def update(self):
        self.bundle = bundle = ActivityBundle(self.source_dir)
        self.version = bundle.get_activity_version()
        self.activity_name = bundle.get_name()
        self.bundle_id = bundle.get_bundle_id()
        self.bundle_name = reduce(lambda x, y: x+y, self.activity_name.split())
        self.bundle_root_dir = self.bundle_name + '.activity'
        self.tar_root_dir = '%s-%d' % (self.bundle_name, self.version)

        if self.dist_name:
            self.xo_name = self.tar_name = self.dist_name
        else:
            self.xo_name = '%s-%d.xo' % (self.bundle_name, self.version)
            self.tar_name = '%s-%d.tar.bz2' % (self.bundle_name, self.version)


class Builder(object):

    def __init__(self, config):
        self.config = config

    def build(self):
        self.build_locale()

    def build_locale(self):
        po_dir = os.path.join(self.config.source_dir, 'po')

        if not self.config.bundle.is_dir(po_dir):
            logging.warn("Missing po/ dir, cannot build_locale")
            return

        locale_dir = os.path.join(self.config.source_dir, 'locale')

        if os.path.exists(locale_dir):
            shutil.rmtree(locale_dir)

        for f in os.listdir(po_dir):
            if not f.endswith('.po') or f == 'pseudo.po':
                continue

            file_name = os.path.join(po_dir, f)
            lang = f[:-3]

            localedir = os.path.join(self.config.source_dir, 'locale', lang)
            mo_path = os.path.join(localedir, 'LC_MESSAGES')
            if not os.path.isdir(mo_path):
                os.makedirs(mo_path)

            mo_file = os.path.join(mo_path, "%s.mo" % self.config.bundle_id)
            args = ["msgfmt", "--output-file=%s" % mo_file, file_name]
            retcode = subprocess.call(args)
            if retcode:
                print 'ERROR - msgfmt failed with return code %i.' % retcode

            cat = gettext.GNUTranslations(open(mo_file, 'r'))
            translated_name = cat.gettext(self.config.activity_name)
            linfo_file = os.path.join(localedir, 'activity.linfo')
            f = open(linfo_file, 'w')
            f.write('[Activity]\nname = %s\n' % translated_name)
            f.close()

    def get_files(self):
        files = self.config.bundle.get_files()

        if not files:
            logging.error('No files found, fixing the MANIFEST.')
            self.fix_manifest()
            files = self.config.bundle.get_files()

        return files

    def check_manifest(self):
        missing_files = []

        allfiles = list_files(self.config.source_dir,
                              IGNORE_DIRS, IGNORE_FILES)
        for path in allfiles:
            if path not in self.config.bundle.manifest:
                missing_files.append(path)

        return missing_files

    def fix_manifest(self):
        self.build()

        manifest = self.config.bundle.manifest

        for path in self.check_manifest():
            manifest.append(path)

        f = open(os.path.join(self.config.source_dir, "MANIFEST"), "wb")
        for line in manifest:
            f.write(line + "\n")


class Packager(object):

    def __init__(self, config):
        self.config = config
        self.package_path = None

        if not os.path.exists(self.config.dist_dir):
            os.mkdir(self.config.dist_dir)


class XOPackager(Packager):

    def __init__(self, builder):
        Packager.__init__(self, builder.config)

        self.builder = builder
        self.package_path = os.path.join(self.config.dist_dir,
                                         self.config.xo_name)

    def package(self):
        bundle_zip = zipfile.ZipFile(self.package_path, 'w',
                                     zipfile.ZIP_DEFLATED)

        missing_files = self.builder.check_manifest()
        if missing_files:
            logging.warn('These files are not included in the manifest ' \
                         'and will not be present in the bundle:\n\n' +
                         '\n'.join(missing_files) +
                         '\n\nUse fix_manifest if you want to add them.')

        for f in self.builder.get_files():
            bundle_zip.write(os.path.join(self.config.source_dir, f),
                             os.path.join(self.config.bundle_root_dir, f))

        bundle_zip.close()


class SourcePackager(Packager):

    def __init__(self, config):
        Packager.__init__(self, config)
        self.package_path = os.path.join(self.config.dist_dir,
                                         self.config.tar_name)

    def get_files(self):
        git_ls = subprocess.Popen(['git', 'ls-files'], stdout=subprocess.PIPE,
                                  cwd=self.config.source_dir)
        stdout, _ = git_ls.communicate()
        if git_ls.returncode:
            # Fall back to filtered list
            return list_files(self.config.source_dir,
                              IGNORE_DIRS, IGNORE_FILES)

        return [path.strip() for path in stdout.strip('\n').split('\n')]

    def package(self):
        tar = tarfile.open(self.package_path, 'w:bz2')
        for f in self.get_files():
            tar.add(os.path.join(self.config.source_dir, f),
                    os.path.join(self.config.tar_root_dir, f))
        tar.close()


class Installer(object):
    IGNORES = ['po/*', 'MANIFEST', 'AUTHORS']

    def __init__(self, builder):
        self.config = builder.config
        self.builder = builder

    def should_ignore(self, f):
        for pattern in self.IGNORES:
            if fnmatch(f, pattern):
                return True
        return False

    def install(self, prefix):
        self.builder.build()

        activity_path = os.path.join(prefix, 'share', 'sugar', 'activities',
                                     self.config.bundle_root_dir)

        source_to_dest = {}
        for f in self.builder.get_files():
            if self.should_ignore(f):
                pass
            elif f.startswith('locale/') and f.endswith('.mo'):
                source_to_dest[f] = os.path.join(prefix, 'share', f)
            else:
                source_to_dest[f] = os.path.join(activity_path, f)

        for source, dest in source_to_dest.items():
            print 'Install %s to %s.' % (source, dest)

            path = os.path.dirname(dest)
            if not os.path.exists(path):
                os.makedirs(path)

            shutil.copy(source, dest)


def cmd_dev(config, args):
    '''Setup for development'''

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
    '''Create a xo bundle package'''

    if args:
        print 'Usage: %prog dist_xo'
        return

    packager = XOPackager(Builder(config))
    packager.package()


def cmd_fix_manifest(config, args):
    '''Add missing files to the manifest'''

    if args:
        print 'Usage: %prog fix_manifest'
        return

    builder = Builder(config)
    builder.fix_manifest()


def cmd_dist_source(config, args):
    '''Create a tar source package'''

    if args:
        print 'Usage: %prog dist_source'
        return

    packager = SourcePackager(config)
    packager.package()


def cmd_install(config, args):
    '''Install the activity in the system'''

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
    '''Generate the gettext pot file'''

    if args:
        print 'Usage: %prog genpot'
        return

    po_path = os.path.join(config.source_dir, 'po')
    if not os.path.isdir(po_path):
        os.mkdir(po_path)

    python_files = []
    for root, dirs_dummy, files in os.walk(config.source_dir):
        for file_name in files:
            if file_name.endswith('.py'):
                python_files.append(os.path.join(root, file_name))

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
    f.close()

    args = ['xgettext', '--join-existing', '--language=Python',
        '--keyword=_', '--add-comments=TRANS:', '--output=%s' % pot_file]

    args += python_files
    retcode = subprocess.call(args)
    if retcode:
        print 'ERROR - xgettext failed with return code %i.' % retcode


def cmd_build(config, args):
    '''Build generated files'''

    if args:
        print 'Usage: %prog build'
        return

    builder = Builder(config)
    builder.build()


def print_commands():
    print 'Available commands:\n'

    for name, func in globals().items():
        if name.startswith('cmd_'):
            print "%-20s %s" % (name.replace('cmd_', ''), func.__doc__)

    print '\n(Type "./setup.py <command> --help" for help about a ' \
          'particular command\'s options.'


def start(bundle_name=None):
    if bundle_name:
        logging.warn("bundle_name deprecated, now comes from activity.info")

    parser = OptionParser(usage='[action] [options]')
    parser.disable_interspersed_args()
    (options_, args) = parser.parse_args()

    config = Config()

    try:
        globals()['cmd_' + args[0]](config, args[1:])
    except (KeyError, IndexError):
        print_commands()


if __name__ == '__main__':
    start()

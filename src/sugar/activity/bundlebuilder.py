# Copyright (C) 2006-2007 Red Hat, Inc.
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

import os
import zipfile
import shutil
import subprocess
import re
import gettext
from optparse import OptionParser

from sugar import env
from sugar.bundle.activitybundle import ActivityBundle

class Config(object):
    def __init__(self, bundle_name, manifest):
        self.bundle_name = bundle_name
        self.manifest = manifest
        self.source_dir = os.getcwd()
        self.bundle_root_dir = self.bundle_name + '.activity'

        bundle = ActivityBundle(self.source_dir)
        self.xo_name = '%s-%d.xo' % (
                self.bundle_name, bundle.get_activity_version())
        self.bundle_id = bundle.get_bundle_id()

        info_path = os.path.join(self.source_dir, 'activity', 'activity.info')
        f = open(info_path,'r')
        info = f.read()
        f.close()
        match = re.search('^name\s*=\s*(.*)$', info, flags = re.MULTILINE)
        self.activity_name = match.group(1)

class _SvnFileList(list):
    def __init__(self):
        f = os.popen('svn list -R')
        for line in f.readlines():
            filename = line.strip()
            if os.path.isfile(filename):
                self.append(filename)
        f.close()

class _GitFileList(list):
    def __init__(self):
        f = os.popen('git-ls-files')
        for line in f.readlines():
            filename = line.strip()
            if not filename.startswith('.'):
                self.append(filename)
        f.close()

class _DefaultFileList(list):
    def __init__(self):
        for name in os.listdir('activity'):
            if name.endswith('.svg'):
                self.append(os.path.join('activity', name))

        self.append('activity/activity.info')

class _ManifestFileList(_DefaultFileList):
    def __init__(self, manifest):
        _DefaultFileList.__init__(self)
        self.append(manifest)

        f = open(manifest,'r')
        for line in f.readlines():
            stripped_line = line.strip()
            if stripped_line and not stripped_line in self:
                self.append(stripped_line)
        f.close()

class _AllFileList(list):
    def __init__(self):
        for root, dirs, files in os.walk('.'):
            if not root.startswith('./locale'):
                for f in files:
                    if not f.endswith('.xo') and \
                       f != '.gitignore':
                        self.append(os.path.join(root, f))

def _get_file_list(manifest):
    if os.path.isfile(manifest):
        return _ManifestFileList(manifest)
    elif os.path.isdir('.git'):
        return _GitFileList()
    elif os.path.isdir('.svn'):
        return _SvnFileList()
    else:
        return _AllFileList()

def _get_po_list(manifest):
    file_list = {}

    po_regex = re.compile("po/(.*)\.po$")
    for file_name in _get_file_list(manifest):
        match = po_regex.match(file_name)
        if match:
            file_list[match.group(1)] = file_name

    return file_list

def _get_l10n_list(config):
    l10n_list = []

    for lang in _get_po_list(config.manifest).keys():
        filename = config.bundle_id + '.mo'
        l10n_list.append(os.path.join('locale', lang, 'LC_MESSAGES', filename))
        l10n_list.append(os.path.join('locale', lang, 'activity.linfo'))

    return l10n_list

def cmd_help(config, options, args):
    print 'Usage: \n\
setup.py build               - build generated files \n\
setup.py dev                 - setup for development \n\
setup.py dist                - create a bundle package \n\
setup.py install   [dirname] - install the bundle \n\
setup.py uninstall [dirname] - uninstall the bundle \n\
setup.py genpot              - generate the gettext pot file \n\
setup.py release             - do a new release of the bundle \n\
setup.py help                - print this message \n\
'

def cmd_dev(config, options, args):
    bundle_path = env.get_user_activities_path()
    if not os.path.isdir(bundle_path):
        os.mkdir(bundle_path)
    bundle_path = os.path.join(bundle_path, config.bundle_top_dir)
    try:
        os.symlink(config.source_dir, bundle_path)
    except OSError:
        if os.path.islink(bundle_path):
            print 'ERROR - The bundle has been already setup for development.'
        else:
            print 'ERROR - A bundle with the same name is already installed.'

def cmd_dist(config, options, args):
    cmd_build(config, options, args)

    file_list = _get_file_list(config.manifest)

    zipname = config.xo_name
    bundle_zip = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)
    base_dir = config.bundle_root_dir
    
    for filename in file_list:
        bundle_zip.write(filename, os.path.join(base_dir, filename))

    for filename in _get_l10n_list(config):
        bundle_zip.write(filename, os.path.join(base_dir, filename))

    bundle_zip.close()

def cmd_install(config, options, args):
    path = args[0]

    cmd_dist(config, options, args)

    root_path = os.path.join(args[0], config.bundle_root_dir)
    if os.path.isdir(root_path):
        shutil.rmtree(root_path)

    if not os.path.exists(path):
        os.mkdir(path)

    zf = zipfile.ZipFile(config.xo_name)

    for name in zf.namelist():
        full_path = os.path.join(path, name)            
        if not os.path.exists(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))

        outfile = open(full_path, 'wb')
        outfile.write(zf.read(name))
        outfile.flush()
        outfile.close()

def cmd_genpot(config, options, args):
    po_path = os.path.join(config.source_dir, 'po')
    if not os.path.isdir(po_path):
        os.mkdir(po_path)

    python_files = []
    file_list = _get_file_list(config.manifest)
    for file_name in file_list:
        if file_name.endswith('.py'):
            python_files.append(file_name)

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

    args = [ 'xgettext', '--join-existing', '--language=Python',
             '--keyword=_', '--add-comments=TRANS:', '--output=%s' % pot_file ]

    args += python_files
    retcode = subprocess.call(args)
    if retcode:
        print 'ERROR - xgettext failed with return code %i.' % retcode

def cmd_release(config, options, args):
    if not os.path.isdir('.git'):
        print 'ERROR - this command works only for git repositories'

    retcode = subprocess.call(['git', 'pull'])
    if retcode:
        print 'ERROR - cannot pull from git'

    print 'Bumping activity version...'

    info_path = os.path.join(config.source_dir, 'activity', 'activity.info')
    f = open(info_path,'r')
    info = f.read()
    f.close()

    exp = re.compile('activity_version\s?=\s?([0-9]*)')
    match = re.search(exp, info)
    version = int(match.group(1)) + 1
    info = re.sub(exp, 'activity_version = %d' % version, info)

    f = open(info_path, 'w')
    f.write(info)
    f.close()

    news_path = os.path.join(config.source_dir, 'NEWS')

    if os.environ.has_key('SUGAR_NEWS'):
        print 'Update NEWS.sugar...'

        sugar_news_path = os.environ['SUGAR_NEWS']
        if os.path.isfile(sugar_news_path):
            f = open(sugar_news_path,'r')
            sugar_news = f.read()
            f.close()
        else:
            sugar_news = ''

        sugar_news += '%s - %d\n\n' % (config.bundle_name, version)

        f = open(news_path,'r')
        for line in f.readlines():
            if len(line.strip()) > 0:
                sugar_news += line
            else:
                break
        f.close()

        sugar_news += '\n'

        f = open(sugar_news_path, 'w')
        f.write(sugar_news)
        f.close()

    print 'Update NEWS...'

    f = open(news_path,'r')
    news = f.read()
    f.close()

    news = '%d\n\n' % version + news

    f = open(news_path, 'w')
    f.write(news)
    f.close()

    print 'Committing to git...'

    changelog = 'Release version %d.' % version
    retcode = subprocess.call(['git', 'commit', '-a', '-m % s' % changelog])
    if retcode:
        print 'ERROR - cannot commit to git'

    retcode = subprocess.call(['git', 'push'])
    if retcode:
        print 'ERROR - cannot push to git'

    print 'Creating the bundle...'
    cmd_dist(config, options, args)

    print 'Done.'

def cmd_build(config, options, args):
    po_list = _get_po_list(config.manifest)
    for lang in po_list.keys():
        file_name = po_list[lang]

        localedir = os.path.join(config.source_dir, 'locale', lang)
        mo_path = os.path.join(localedir, 'LC_MESSAGES')
        if not os.path.isdir(mo_path):
            os.makedirs(mo_path)

        mo_file = os.path.join(mo_path, "%s.mo" % config.bundle_id)
        args = ["msgfmt", "--output-file=%s" % mo_file, file_name]
        retcode = subprocess.call(args)
        if retcode:
            print 'ERROR - msgfmt failed with return code %i.' % retcode

        cat = gettext.GNUTranslations(open(mo_file, 'r'))
        translated_name = cat.gettext(config.activity_name)
        linfo_file = os.path.join(localedir, 'activity.linfo')
        f = open(linfo_file, 'w')
        f.write('[Activity]\nname = %s\n' % translated_name)
        f.close()

def start(bundle_name, manifest='MANIFEST'):
    parser = OptionParser()
    (options, args) = parser.parse_args()

    config = Config(bundle_name, manifest)

    try:
        globals()['cmd_' + args[0]](config, options, args[1:])
    except (KeyError, IndexError):
        cmd_help(config, options, args)

if __name__ == '__main__':
    start()

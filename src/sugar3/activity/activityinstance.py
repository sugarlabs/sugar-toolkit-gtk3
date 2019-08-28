# Copyright (C) 2006-2008, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import sys
import six
import logging

# Change the default encoding to avoid UnicodeDecodeError
# http://lists.sugarlabs.org/archive/sugar-devel/2012-August/038928.html
if six.PY2:
    reload(sys)
    sys.setdefaultencoding('utf-8')

import gettext
from optparse import OptionParser

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

from sugar3.activity import activityhandle
from sugar3 import config
from sugar3.bundle.activitybundle import ActivityBundle
from sugar3 import logger

from sugar3.bundle.bundle import MalformedBundleException

from errno import EEXIST

import time
import hashlib
import random


def _makedirs(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != EEXIST:
            raise e


def create_activity_instance(constructor, handle):
    activity = constructor(handle)
    activity.show()
    return activity


def get_single_process_name(bundle_id):
    return bundle_id


def get_single_process_path(bundle_id):
    return '/' + bundle_id.replace('.', '/')


class SingleProcess(dbus.service.Object):

    def __init__(self, name_service, constructor):
        self.constructor = constructor

        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(name_service, bus=bus)
        object_path = get_single_process_path(name_service)
        dbus.service.Object.__init__(self, bus_name, object_path)

    @dbus.service.method('org.laptop.SingleProcess', in_signature='a{sv}')
    def create(self, handle_dict):
        handle = activityhandle.create_from_dict(handle_dict)
        create_activity_instance(self.constructor, handle)


def main():
    usage = 'usage: %prog [options] [activity dir] [python class]'
    epilog = 'If you are running from a directory containing an Activity, ' \
             'the argument may be omitted.  Otherwise please provide either '\
             'a directory containing a Sugar Activity [activity dir], a '\
             '[python_class], or both.'

    parser = OptionParser(usage=usage, epilog=epilog)
    parser.add_option('-b', '--bundle-id', dest='bundle_id',
                      help='identifier of the activity bundle')
    parser.add_option('-a', '--activity-id', dest='activity_id',
                      help='identifier of the activity instance')
    parser.add_option('-o', '--object-id', dest='object_id',
                      help='identifier of the associated datastore object')
    parser.add_option('-u', '--uri', dest='uri',
                      help='URI to load')
    parser.add_option('-s', '--single-process', dest='single_process',
                      action='store_true',
                      help='start all the instances in the same process')
    parser.add_option('-i', '--invited', dest='invited',
                      action='store_true', default=False,
                      help='the activity is being launched for handling an '
                           'invite from the network')
    (options, args) = parser.parse_args()

    logger.start()

    activity_class = None
    if len(args) == 2:
        activity_class = args[1]
        os.chdir(args[0])
    elif len(args) == 1:
        if os.path.isdir(args[0]):
            os.chdir(args[0])
        else:
            activity_class = args[0]

    bundle_path = os.path.abspath(os.curdir)
    sys.path.insert(0, bundle_path)

    try:
        bundle = ActivityBundle(bundle_path)
    except MalformedBundleException:
        parser.print_help()
        exit(0)

    if not activity_class:
        command = bundle.get_command()
        if command.startswith('sugar-activity'):
            if not command.startswith('sugar-activity3'):
                logging.warning("Activity written for Python 2,"
                                " consider porting to Python 3.")
            activity_class = command.split(" ")[1]

    # when an activity is started outside sugar,
    # activityfactory.get_environment has not executed in parent
    # process, so parts of get_environment must happen here.
    if 'SUGAR_BUNDLE_PATH' not in os.environ:
        profile_id = os.environ.get('SUGAR_PROFILE', 'default')
        home_dir = os.environ.get('SUGAR_HOME', os.path.expanduser('~/.sugar'))
        base = os.path.join(home_dir, profile_id)
        activity_root = os.path.join(base, bundle.get_bundle_id())

        instance_dir = os.path.join(activity_root, 'instance')
        _makedirs(instance_dir)

        data_dir = os.path.join(activity_root, 'data')
        _makedirs(data_dir)

        tmp_dir = os.path.join(activity_root, 'tmp')
        _makedirs(tmp_dir)

        os.environ['SUGAR_BUNDLE_PATH'] = bundle_path
        os.environ['SUGAR_BUNDLE_ID'] = bundle.get_bundle_id()
        os.environ['SUGAR_ACTIVITY_ROOT'] = activity_root

    os.environ['SUGAR_BUNDLE_NAME'] = bundle.get_name()
    os.environ['SUGAR_BUNDLE_VERSION'] = str(bundle.get_activity_version())

    # must be done early, some activities set translations globally, SL #3654
    activity_locale_path = os.environ.get("SUGAR_LOCALEDIR",
                                          config.locale_path)

    gettext.bindtextdomain(bundle.get_bundle_id(), activity_locale_path)
    gettext.bindtextdomain('sugar-toolkit-gtk3', config.locale_path)
    gettext.textdomain(bundle.get_bundle_id())

    splitted_module = activity_class.rsplit('.', 1)
    module_name = splitted_module[0]
    class_name = splitted_module[1]

    module = __import__(module_name)
    for comp in module_name.split('.')[1:]:
        module = getattr(module, comp)

    activity_constructor = getattr(module, class_name)

    if not options.activity_id:
        # Generate random hash
        data = '%s%s' % (time.time(), random.randint(10000, 100000))
        random_hash = hashlib.sha1(data.encode()).hexdigest()
        options.activity_id = random_hash
        options.bundle_id = bundle.get_bundle_id()

    activity_handle = activityhandle.ActivityHandle(
        activity_id=options.activity_id,
        object_id=options.object_id, uri=options.uri,
        invited=options.invited)

    if options.single_process is True:
        sessionbus = dbus.SessionBus()

        service_name = get_single_process_name(options.bundle_id)
        service_path = get_single_process_path(options.bundle_id)

        bus_object = sessionbus.get_object(
            'org.freedesktop.DBus', '/org/freedesktop/DBus')
        try:
            name = bus_object.GetNameOwner(
                service_name, dbus_interface='org.freedesktop.DBus')
        except dbus.DBusException:
            name = None

        if not name:
            SingleProcess(service_name, activity_constructor)
        else:
            try:
                single_process = sessionbus.get_object(service_name,
                                                       service_path)
                single_process.create(
                    activity_handle.get_dict(),
                    dbus_interface='org.laptop.SingleProcess')

                print('Created %s in a single process.' % service_name)
                sys.exit(0)
            except (TypeError, dbus.DBusException):
                print('Could not communicate with the instance process,'
                      'launching a new process')

    if hasattr(module, 'start'):
        module.start()

    instance = create_activity_instance(activity_constructor, activity_handle)

    if hasattr(instance, 'run_main_loop'):
        instance.run_main_loop()

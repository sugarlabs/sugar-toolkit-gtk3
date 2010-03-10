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

"""Shell side object which manages request to start activity

UNSTABLE. Activities are currently not allowed to run other activities so at
the moment there is no reason to stabilize this API.
"""

import logging

import dbus
import gobject

from sugar.presence import presenceservice
from sugar.activity.activityhandle import ActivityHandle
from sugar import util
from sugar import env
from sugar.datastore import datastore

from errno import EEXIST, ENOSPC

import os
import tempfile
import subprocess
import pwd

_SHELL_SERVICE = "org.laptop.Shell"
_SHELL_PATH = "/org/laptop/Shell"
_SHELL_IFACE = "org.laptop.Shell"

_ACTIVITY_FACTORY_INTERFACE = "org.laptop.ActivityFactory"

# helper method to close all filedescriptors
# borrowed from subprocess.py
try:
    MAXFD = os.sysconf("SC_OPEN_MAX")
except ValueError:
    MAXFD = 256


def _close_fds():
    for i in xrange(3, MAXFD):
        try:
            os.close(i)
        # pylint: disable-msg=W0704
        except Exception:
            pass


def create_activity_id():
    """Generate a new, unique ID for this activity"""
    pservice = presenceservice.get_instance()

    # create a new unique activity ID
    i = 0
    act_id = None
    while i < 10:
        act_id = util.unique_id()
        i += 1

        # check through network activities
        found = False
        activities = pservice.get_activities()
        for act in activities:
            if act_id == act.props.id:
                found = True
                break
        if not found:
            return act_id
    raise RuntimeError("Cannot generate unique activity id.")


def get_environment(activity):
    environ = os.environ.copy()

    bin_path = os.path.join(activity.get_path(), 'bin')

    activity_root = env.get_profile_path(activity.get_bundle_id())
    if not os.path.exists(activity_root):
        os.mkdir(activity_root)

    data_dir = os.path.join(activity_root, 'instance')
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)

    data_dir = os.path.join(activity_root, 'data')
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)

    tmp_dir = os.path.join(activity_root, 'tmp')
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    environ['SUGAR_BUNDLE_PATH'] = activity.get_path()
    environ['SUGAR_BUNDLE_ID'] = activity.get_bundle_id()
    environ['SUGAR_ACTIVITY_ROOT'] = activity_root
    environ['PATH'] = bin_path + ':' + environ['PATH']

    if activity.get_path().startswith(env.get_user_activities_path()):
        environ['SUGAR_LOCALEDIR'] = os.path.join(activity.get_path(),
            'locale')

    return environ


def get_command(activity, activity_id=None, object_id=None, uri=None):
    if not activity_id:
        activity_id = create_activity_id()

    command = activity.get_command().split(' ')
    command.extend(['-b', activity.get_bundle_id()])
    command.extend(['-a', activity_id])

    if object_id is not None:
        command.extend(['-o', object_id])
    if uri is not None:
        command.extend(['-u', uri])

    # if the command is in $BUNDLE_ROOT/bin, execute the absolute path so there
    # is no need to mangle with the shell's PATH
    if '/' not in command[0]:
        bin_path = os.path.join(activity.get_path(), 'bin')
        absolute_path = os.path.join(bin_path, command[0])
        if os.path.exists(absolute_path):
            command[0] = absolute_path

    logging.debug('launching: %r', command)

    return command


def open_log_file(activity):
    i = 1
    while True:
        path = env.get_logs_path('%s-%s.log' % (activity.get_bundle_id(), i))
        try:
            fd = os.open(path, os.O_EXCL | os.O_CREAT | os.O_WRONLY, 0644)
            f = os.fdopen(fd, 'w', 0)
            return (path, f)
        except OSError, e:
            if e.errno == EEXIST:
                i += 1
            elif e.errno == ENOSPC:
                # not the end of the world; let's try to keep going.
                return ('/dev/null', open('/dev/null', 'w'))
            else:
                raise e


class ActivityCreationHandler(gobject.GObject):
    """Sugar-side activity creation interface

    This object uses a dbus method on the ActivityFactory
    service to create the new activity.  It generates
    GObject events in response to the success/failure of
    activity startup using callbacks to the service's
    create call.
    """

    def __init__(self, bundle, handle):
        """Initialise the handler

        bundle -- the ActivityBundle to launch
        activity_handle -- stores the values which are to
            be passed to the service to uniquely identify
            the activity to be created and the sharing
            service that may or may not be connected with it

            sugar.activity.activityhandle.ActivityHandle instance

        calls the "create" method on the service for this
        particular activity type and registers the
        _reply_handler and _error_handler methods on that
        call's results.

        The specific service which creates new instances of this
        particular type of activity is created during the activity
        registration process in shell bundle registry which creates
        service definition files for each registered bundle type.

        If the file '/etc/olpc-security' exists, then activity launching
        will be delegated to the prototype 'Rainbow' security service.
        """
        gobject.GObject.__init__(self)

        self._bundle = bundle
        self._service_name = bundle.get_bundle_id()
        self._handle = handle

        bus = dbus.SessionBus()
        bus_object = bus.get_object(_SHELL_SERVICE, _SHELL_PATH)
        self._shell = dbus.Interface(bus_object, _SHELL_IFACE)

        if handle.activity_id is not None and handle.object_id is None:
            datastore.find({'activity_id': self._handle.activity_id},
                           reply_handler=self._find_object_reply_handler,
                           error_handler=self._find_object_error_handler)
        else:
            self._launch_activity()

    def _launch_activity(self):
        if self._handle.activity_id != None:
            self._shell.ActivateActivity(self._handle.activity_id,
                        reply_handler=self._activate_reply_handler,
                        error_handler=self._activate_error_handler)
        else:
            self._create_activity()

    def _create_activity(self):
        if self._handle.activity_id is None:
            self._handle.activity_id = create_activity_id()

        self._shell.NotifyLaunch(
                    self._service_name, self._handle.activity_id,
                    reply_handler=self._no_reply_handler,
                    error_handler=self._notify_launch_error_handler)

        environ = get_environment(self._bundle)
        (log_path, log_file) = open_log_file(self._bundle)
        command = get_command(self._bundle, self._handle.activity_id,
                              self._handle.object_id,
                              self._handle.uri)

        dev_null = file('/dev/null', 'w')
        environment_dir = None
        rainbow_found = subprocess.call(['which', 'rainbow-run'],
            stdout=dev_null, stderr=dev_null) == 0
        use_rainbow = rainbow_found and os.path.exists('/etc/olpc-security')
        if use_rainbow:
            environment_dir = tempfile.mkdtemp()
            command = ['sudo', '-E', '--',
                       'rainbow-run',
                       '-v', '-v',
                       '-a', 'rainbow-sugarize',
                       '-s', '/var/spool/rainbow/2',
                       '-f', '1',
                       '-f', '2',
                       '-c', self._bundle.get_path(),
                       '-u', pwd.getpwuid(os.getuid()).pw_name,
                       '-i', environ['SUGAR_BUNDLE_ID'],
                       '-e', environment_dir,
                       '--',
                      ] + command

            for key, value in environ.items():
                file_path = os.path.join(environment_dir, str(key))
                open(file_path, 'w').write(str(value))

            log_file.write(' '.join(command) + '\n\n')

        dev_null = file('/dev/null', 'r')
        child = subprocess.Popen([str(s) for s in command],
            env=environ,
            cwd=str(self._bundle.get_path()),
            close_fds=True,
            stdin=dev_null.fileno(),
            stdout=log_file.fileno(),
            stderr=log_file.fileno())

        gobject.child_watch_add(child.pid,
                                _child_watch_cb,
                                (environment_dir, log_file,
                                    self._handle.activity_id))

    def _no_reply_handler(self, *args):
        pass

    def _notify_launch_failure_error_handler(self, err):
        logging.error('Notify launch failure failed %s', err)

    def _notify_launch_error_handler(self, err):
        logging.debug('Notify launch failed %s', err)

    def _activate_reply_handler(self, activated):
        if not activated:
            self._create_activity()

    def _activate_error_handler(self, err):
        logging.error('Activity activation request failed %s', err)

    def _create_reply_handler(self):
        logging.debug('Activity created %s (%s).',
            self._handle.activity_id, self._service_name)

    def _create_error_handler(self, err):
        logging.error("Couldn't create activity %s (%s): %s",
            self._handle.activity_id, self._service_name, err)
        self._shell.NotifyLaunchFailure(
            self._handle.activity_id, reply_handler=self._no_reply_handler,
            error_handler=self._notify_launch_failure_error_handler)

    def _find_object_reply_handler(self, jobjects, count):
        if count > 0:
            if count > 1:
                logging.debug("Multiple objects has the same activity_id.")
            self._handle.object_id = jobjects[0]['uid']
        self._launch_activity()

    def _find_object_error_handler(self, err):
        logging.error('Datastore find failed %s', err)
        self._launch_activity()


def create(bundle, activity_handle=None):
    """Create a new activity from its name."""
    if not activity_handle:
        activity_handle = ActivityHandle()
    return ActivityCreationHandler(bundle, activity_handle)


def create_with_uri(bundle, uri):
    """Create a new activity and pass the uri as handle."""
    activity_handle = ActivityHandle(uri=uri)
    return ActivityCreationHandler(bundle, activity_handle)


def create_with_object_id(bundle, object_id):
    """Create a new activity and pass the object id as handle."""
    activity_handle = ActivityHandle(object_id=object_id)
    return ActivityCreationHandler(bundle, activity_handle)


def _child_watch_cb(pid, condition, user_data):
    # FIXME we use standalone method here instead of ActivityCreationHandler's
    # member to have workaround code, see #1123
    environment_dir, log_file, activity_id = user_data
    if environment_dir is not None:
        subprocess.call(['/bin/rm', '-rf', environment_dir])

    if os.WIFEXITED(condition):
        status = os.WEXITSTATUS(condition)
        signum = None
        message = 'Exited with status %s' % status
    elif os.WIFSIGNALED(condition):
        status = None
        signum = os.WTERMSIG(condition)
        message = 'Terminated by signal %s' % signum
    else:
        status = None
        signum = os.WTERMSIG(condition)
        message = 'Undefined status with signal %s' % signum

    try:
        log_file.write('%s, pid %s data %s\n' % (message, pid, user_data))
    finally:
        log_file.close()

    # try to reap zombies in case SIGCHLD has not been set to SIG_IGN
    try:
        os.waitpid(pid, 0)
    except OSError:
        # SIGCHLD = SIG_IGN, no zombies
        pass

    if status or signum:
        # XXX have to recreate dbus object since we can't reuse
        # ActivityCreationHandler's one, see
        # https://bugs.freedesktop.org/show_bug.cgi?id=23507
        bus = dbus.SessionBus()
        bus_object = bus.get_object(_SHELL_SERVICE, _SHELL_PATH)
        shell = dbus.Interface(bus_object, _SHELL_IFACE)

        def reply_handler_cb(*args):
            pass

        def error_handler_cb(error):
            logging.error('Cannot send NotifyLaunchFailure to the shell')

        # TODO send launching failure but activity could already show
        # main window, see http://bugs.sugarlabs.org/ticket/1447#comment:19
        shell.NotifyLaunchFailure(activity_id,
                reply_handler=reply_handler_cb,
                error_handler=error_handler_cb)

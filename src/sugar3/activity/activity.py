# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2007-2009 One Laptop Per Child
# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
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
Activity
========

A definitive reference for what a Sugar Python activity must do to
participate in the Sugar desktop.

.. note:: This API is STABLE.

The :class:`Activity` class is used to derive all Sugar Python
activities.  This is where your activity starts.

**Derive from the class**

    .. code-block:: python

        from sugar3.activity.activity import Activity

        class MyActivity(Activity):
            def __init__(self, handle):
                Activity.__init__(self, handle)

    An activity must implement a new class derived from
    :class:`Activity`.

    Name the new class `MyActivity`, where `My` is the name of your
    activity.  Use bundle metadata to tell Sugar to instantiate this
    class.  See :class:`~sugar3.bundle` for bundle metadata.

**Create a ToolbarBox**

    In your :func:`__init__` method create a
    :class:`~sugar3.graphics.toolbarbox.ToolbarBox`, with an
    :class:`~sugar3.activity.widgets.ActivityToolbarButton`, a
    :class:`~sugar3.activity.widgets.StopButton`, and then call
    :func:`~sugar3.graphics.window.Window.set_toolbar_box`.

    .. code-block:: python
        :emphasize-lines: 2-4,10-

        from sugar3.activity.activity import Activity
        from sugar3.graphics.toolbarbox import ToolbarBox
        from sugar3.activity.widgets import ActivityToolbarButton
        from sugar3.activity.widgets import StopButton

        class MyActivity(Activity):
            def __init__(self, handle):
                Activity.__init__(self, handle)

                toolbar_box = ToolbarBox()
                activity_button = ActivityToolbarButton(self)
                toolbar_box.toolbar.insert(activity_button, 0)
                activity_button.show()

                separator = Gtk.SeparatorToolItem(draw=False)
                separator.set_expand(True)
                toolbar_box.toolbar.insert(separator, -1)
                separator.show()

                stop_button = StopButton(self)
                toolbar_box.toolbar.insert(stop_button, -1)
                stop_button.show()

                self.set_toolbar_box(toolbar_box)
                toolbar_box.show()

**Journal methods**

    In your activity class, code
    :func:`~sugar3.activity.activity.Activity.read_file()` and
    :func:`~sugar3.activity.activity.Activity.write_file()` methods.

    Most activities create and resume journal objects.  For example,
    the Write activity saves the document as a journal object, and
    reads it from the journal object when resumed.

    :func:`~sugar3.activity.activity.Activity.read_file()` and
    :func:`~sugar3.activity.activity.Activity.write_file()` will be
    called by the toolkit to tell your activity that it must load or
    save the data the user is working on.

**Activity toolbars**

    Add any activity toolbars before the last separator in the
    :class:`~sugar3.graphics.toolbarbox.ToolbarBox`, so that the
    :class:`~sugar3.activity.widgets.StopButton` is aligned to the
    right.

    There are a number of standard Toolbars.

    You may need the :class:`~sugar3.activity.widgets.EditToolbar`.
    This has copy and paste buttons.  You may derive your own
    class from
    :class:`~sugar3.activity.widgets.EditToolbar`:

    .. code-block:: python

        from sugar3.activity.widgets import EditToolbar

        class MyEditToolbar(EditToolbar):
            ...

    See :class:`~sugar3.activity.widgets.EditToolbar` for the
    methods you should implement in your class.

    You may need some activity specific buttons and options which
    you can create as toolbars by deriving a class from
    :class:`Gtk.Toolbar`:

    .. code-block:: python

        class MySpecialToolbar(Gtk.Toolbar):
            ...

**Sharing**

    An activity can be shared across the network with other users.  Near
    the end of your :func:`__init__`, test if the activity is shared,
    and connect to signals to detect sharing.

    .. code-block:: python

        if self.shared_activity:
            # we are joining the activity
            self.connect('joined', self._joined_cb)
            if self.get_shared():
                # we have already joined
                self._joined_cb()
        else:
            # we are creating the activity
            self.connect('shared', self._shared_cb)

    Add methods to handle the signals.

Read through the methods of the :class:`Activity` class below, to learn
more about how to make an activity work.

Hint: A good and simple activity to learn from is the Read activity.
You may copy it and use it as a template.
'''

import six
import gettext
import logging
import os
import signal
import time
from hashlib import sha1
from functools import partial
import cairo
import json

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('TelepathyGLib', '0.12')
gi.require_version('SugarExt', '1.0')

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import TelepathyGLib
import dbus
import dbus.service
from dbus import PROPERTIES_IFACE

from sugar3 import util
from sugar3 import power
from sugar3.profile import get_color, get_save_as
from sugar3.presence import presenceservice
from sugar3.activity.activityservice import ActivityService
from sugar3.graphics import style
from sugar3.graphics.window import Window
from sugar3.graphics.alert import Alert
from sugar3.graphics.icon import Icon
from sugar3.datastore import datastore
from sugar3.bundle.activitybundle import get_bundle_instance
from sugar3.bundle.helpers import bundle_from_dir
from sugar3 import env
from errno import EEXIST

from gi.repository import SugarExt


def _(msg):
    return gettext.dgettext('sugar-toolkit-gtk3', msg)


SCOPE_PRIVATE = 'private'
SCOPE_INVITE_ONLY = 'invite'  # shouldn't be shown in UI, it's implicit
SCOPE_NEIGHBORHOOD = 'public'

J_DBUS_SERVICE = 'org.laptop.Journal'
J_DBUS_PATH = '/org/laptop/Journal'
J_DBUS_INTERFACE = 'org.laptop.Journal'

N_BUS_NAME = 'org.freedesktop.Notifications'
N_OBJ_PATH = '/org/freedesktop/Notifications'
N_IFACE_NAME = 'org.freedesktop.Notifications'

CHANNEL = TelepathyGLib.IFACE_CHANNEL
CHANNEL_TYPE_TEXT = TelepathyGLib.IFACE_CHANNEL_TYPE_TEXT
CLIENT = TelepathyGLib.IFACE_CLIENT
CLIENT_HANDLER = TelepathyGLib.IFACE_CLIENT_HANDLER

CONNECTION_HANDLE_TYPE_CONTACT = TelepathyGLib.HandleType.CONTACT
CONNECTION_HANDLE_TYPE_ROOM = TelepathyGLib.HandleType.ROOM

CONN_INTERFACE_ACTIVITY_PROPERTIES = 'org.laptop.Telepathy.ActivityProperties'

PREVIEW_SIZE = style.zoom(300), style.zoom(225)
"""
Size of a preview image for journal object metadata.
"""


class _ActivitySession(GObject.GObject):

    __gsignals__ = {
        'quit-requested': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'quit': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self._xsmp_client = SugarExt.ClientXSMP()
        self._xsmp_client.connect('quit-requested',
                                  self.__sm_quit_requested_cb)
        self._xsmp_client.connect('quit', self.__sm_quit_cb)
        self._xsmp_client.startup()

        self._activities = []
        self._will_quit = []

    def register(self, activity):
        self._activities.append(activity)

    def unregister(self, activity):
        self._activities.remove(activity)

        if len(self._activities) == 0:
            logging.debug('Quitting the activity process.')
            Gtk.main_quit()

    def will_quit(self, activity, will_quit):
        if will_quit:
            self._will_quit.append(activity)

            # We can quit only when all the instances agreed to
            for activity in self._activities:
                if activity not in self._will_quit:
                    return

            self._xsmp_client.will_quit(True)
        else:
            self._will_quit = []
            self._xsmp_client.will_quit(False)

    def __sm_quit_requested_cb(self, client):
        self.emit('quit-requested')

    def __sm_quit_cb(self, client):
        self.emit('quit')


class Activity(Window, Gtk.Container):
    """
    Initialise an Activity.

    Args:
        handle (:class:`~sugar3.activity.activityhandle.ActivityHandle`):
            instance providing the activity id and access to the presence
            service which *may* provide sharing for this application

        create_jobject (boolean):
            DEPRECATED: define if it should create a journal object if
            we are not resuming. The parameter is ignored, and always
            will be created a object in the Journal.

    **Signals:**
        * **shared** - the activity has been shared on a network in
            order that other users may join,

        * **joined** - the activity has joined with other instances of
            the activity to create a shared network activity.

    Side effects:

        * sets the gdk screen DPI setting (resolution) to the Sugar
          screen resolution.

        * connects our "destroy" message to our _destroy_cb method.

        * creates a base Gtk.Window within this window.

        * creates an ActivityService (self._bus) servicing this application.

    When your activity implements :func:`__init__`, it must call the
    :class:`Activity` class :func:`__init__` before any
    :class:`Activity` specific code.
    """

    __gtype_name__ = 'SugarActivity'

    __gsignals__ = {
        'shared': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'joined': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        # For internal use only, use can_close() if you want to perform extra
        # checks before actually closing
        '_closing': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, handle, create_jobject=True):
        if hasattr(GLib, 'unix_signal_add'):
            GLib.unix_signal_add(
                GLib.PRIORITY_DEFAULT, signal.SIGINT, self.close)

        # Stuff that needs to be done early
        icons_path = os.path.join(get_bundle_path(), 'icons')
        Gtk.IconTheme.get_default().append_search_path(icons_path)

        sugar_theme = 'sugar-72'
        if 'SUGAR_SCALING' in os.environ:
            if os.environ['SUGAR_SCALING'] == '100':
                sugar_theme = 'sugar-100'

        # This code can be removed when we grow an xsettings daemon (the GTK+
        # init routines will then automatically figure out the font settings)
        settings = Gtk.Settings.get_default()
        settings.set_property('gtk-theme-name', sugar_theme)
        settings.set_property('gtk-icon-theme-name', 'sugar')
        settings.set_property('gtk-button-images', True)
        settings.set_property('gtk-font-name',
                              '%s %f' % (style.FONT_FACE, style.FONT_SIZE))

        Window.__init__(self)

        if 'SUGAR_ACTIVITY_ROOT' in os.environ:
            # If this activity runs inside Sugar, we want it to take all the
            # screen. Would be better if it was the shell to do this, but we
            # haven't found yet a good way to do it there. See #1263.
            self.connect('window-state-event', self.__window_state_event_cb)
            screen = Gdk.Screen.get_default()
            screen.connect('size-changed', self.__screen_size_changed_cb)
            self._adapt_window_to_screen()

        # process titles will only show 15 characters
        # but they get truncated anyway so if more characters
        # are supported in the future we will get a better view
        # of the processes
        proc_title = '%s <%s>' % (get_bundle_name(), handle.activity_id)
        util.set_proc_title(proc_title)

        self.connect('realize', self.__realize_cb)
        self.connect('delete-event', self.__delete_event_cb)

        self._in_main = False
        self._iconify = False
        self._active = False
        self._active_time = None
        self._spent_time = 0
        self._activity_id = handle.activity_id
        self.shared_activity = None
        self._join_id = None
        self._updating_jobject = False
        self._closing = False
        self._quit_requested = False
        self._deleting = False
        self._max_participants = None
        self._invites_queue = []
        self._jobject = None
        self._jobject_old = None
        self._is_resumed = False
        self._read_file_called = False

        self._session = _get_session()
        self._session.register(self)
        self._session.connect('quit-requested',
                              self.__session_quit_requested_cb)
        self._session.connect('quit', self.__session_quit_cb)

        accel_group = Gtk.AccelGroup()
        self.sugar_accel_group = accel_group
        self.add_accel_group(accel_group)

        self._bus = ActivityService(self)
        self._owns_file = False

        share_scope = SCOPE_PRIVATE

        if handle.object_id:
            self._is_resumed = True
            self._jobject = datastore.get(handle.object_id)

            if 'share-scope' in self._jobject.metadata:
                share_scope = self._jobject.metadata['share-scope']

            if 'launch-times' in self._jobject.metadata:
                self._jobject.metadata['launch-times'] += ', %d' % \
                    int(time.time())
            else:
                self._jobject.metadata['launch-times'] = \
                    str(int(time.time()))

            if 'spent-times' in self._jobject.metadata:
                self._jobject.metadata['spent-times'] += ', 0'
            else:
                self._jobject.metadata['spent-times'] = '0'
        else:
            self._is_resumed = False
            self._jobject = self._initialize_journal_object()
            self.set_title(self._jobject.metadata['title'])

        self.shared_activity = None
        self._join_id = None

        self._original_title = self._jobject.metadata['title']

        if handle.invited:
            wait_loop = GObject.MainLoop()
            self._client_handler = _ClientHandler(
                self.get_bundle_id(),
                partial(self.__got_channel_cb, wait_loop))
            # FIXME: The current API requires that self.shared_activity is set
            # before exiting from __init__, so we wait until we have got the
            # shared activity. http://bugs.sugarlabs.org/ticket/2168
            wait_loop.run()
        else:
            pservice = presenceservice.get_instance()
            mesh_instance = pservice.get_activity(self._activity_id,
                                                  warn_if_none=False)
            self._set_up_sharing(mesh_instance, share_scope)

        if self.shared_activity is not None:
            self._jobject.metadata['title'] = self.shared_activity.props.name
            self._jobject.metadata['icon-color'] = \
                self.shared_activity.props.color
        else:
            self._jobject.metadata.connect('updated',
                                           self.__jobject_updated_cb)
        self.set_title(self._jobject.metadata['title'])

        bundle = get_bundle_instance(get_bundle_path())
        self.set_icon_from_file(bundle.get_icon())

        self._busy_count = 0
        self._stop_buttons = []

        if self._is_resumed and get_save_as():
            # preserve original and use a copy for editing
            self._jobject_old = self._jobject
            self._jobject = datastore.copy(self._jobject, '/')

        self._original_title = self._jobject.metadata['title']

    def add_stop_button(self, button):
        """
        Register an extra stop button.  Normally not required.  Use only
        when an activity has more than the default stop button.

        Args:
            button (:class:`Gtk.Button`): a stop button
        """
        self._stop_buttons.append(button)

    def iconify(self):
        if not self._in_main:
            self._iconify = True  # i.e. do after Window.show()
        else:
            Window.iconify(self)

    def run_main_loop(self):
        if self._iconify:
            Window.iconify(self)
        self._in_main = True
        Gtk.main()

    def _initialize_journal_object(self):
        title = _('%s Activity') % get_bundle_name()

        icon_color = get_color().to_string()

        jobject = datastore.create()
        jobject.metadata['title'] = title
        jobject.metadata['title_set_by_user'] = '0'
        jobject.metadata['activity'] = self.get_bundle_id()
        jobject.metadata['activity_id'] = self.get_id()
        jobject.metadata['keep'] = '0'
        jobject.metadata['preview'] = ''
        jobject.metadata['share-scope'] = SCOPE_PRIVATE
        jobject.metadata['icon-color'] = icon_color
        jobject.metadata['launch-times'] = str(int(time.time()))
        jobject.metadata['spent-times'] = '0'
        jobject.file_path = ''

        # FIXME: We should be able to get an ID synchronously from the DS,
        # then call async the actual create.
        # http://bugs.sugarlabs.org/ticket/2169
        datastore.write(jobject)

        return jobject

    def __jobject_updated_cb(self, jobject):
        if self.get_title() == jobject['title']:
            return
        self.set_title(jobject['title'])

    def _set_up_sharing(self, mesh_instance, share_scope):
        # handle activity share/join
        logging.debug('*** Act %s, mesh instance %r, scope %s' %
                      (self._activity_id, mesh_instance, share_scope))
        if mesh_instance is not None:
            # There's already an instance on the mesh, join it
            logging.debug('*** Act %s joining existing mesh instance %r' %
                          (self._activity_id, mesh_instance))
            self.shared_activity = mesh_instance
            self.shared_activity.connect('notify::private',
                                         self.__privacy_changed_cb)
            self._join_id = self.shared_activity.connect('joined',
                                                         self.__joined_cb)
            if not self.shared_activity.props.joined:
                self.shared_activity.join()
            else:
                self.__joined_cb(self.shared_activity, True, None)
        elif share_scope != SCOPE_PRIVATE:
            logging.debug('*** Act %s no existing mesh instance, but used to '
                          'be shared, will share' % self._activity_id)
            # no existing mesh instance, but activity used to be shared, so
            # restart the share
            if share_scope == SCOPE_INVITE_ONLY:
                self.share(private=True)
            elif share_scope == SCOPE_NEIGHBORHOOD:
                self.share(private=False)
            else:
                logging.debug('Unknown share scope %r' % share_scope)

    def __got_channel_cb(self, wait_loop, connection_path, channel_path,
                         handle_type):
        logging.debug('Activity.__got_channel_cb')
        pservice = presenceservice.get_instance()

        if handle_type == CONNECTION_HANDLE_TYPE_ROOM:
            connection_name = connection_path.replace('/', '.')[1:]
            bus = dbus.SessionBus()
            channel = bus.get_object(connection_name, channel_path)
            room_handle = channel.Get(CHANNEL, 'TargetHandle')
            mesh_instance = pservice.get_activity_by_handle(connection_path,
                                                            room_handle)
        else:
            mesh_instance = pservice.get_activity(self._activity_id,
                                                  warn_if_none=False)

        self._set_up_sharing(mesh_instance, SCOPE_PRIVATE)
        wait_loop.quit()

    def get_active(self):
        '''
        Get whether the activity is active.  An activity may be made
        inactive by the shell as a result of another activity being
        active.  An active activity accumulates usage metrics.

        Returns:
            boolean: if the activity is active.
        '''
        return self._active

    def _update_spent_time(self):
        if self._active is True and self._active_time is None:
            self._active_time = time.time()
        elif self._active is False and self._active_time is not None:
            self._spent_time += time.time() - self._active_time
            self._active_time = None
        elif self._active is True and self._active_time is not None:
            current = time.time()
            self._spent_time += current - self._active_time
            self._active_time = current

    def set_active(self, active):
        '''
        Set whether the activity is active.  An activity may declare
        itself active or inactive, as can the shell.  An active activity
        accumulates usage metrics.

        Args:
            active (boolean): if the activity is active.
        '''
        if self._active != active:
            self._active = active
            self._update_spent_time()
            if not self._active and self._jobject:
                self.save()

    active = GObject.Property(
        type=bool, default=False, getter=get_active, setter=set_active)
    '''
        Whether an activity is active.
    '''

    def get_max_participants(self):
        '''
        Get the maximum number of users that can share a instance
        of this activity.  Should be configured in the activity.info
        file.  When not configured, it will be zero.

        Returns:
            int: the maximum number of participants

        See also
        :func:`~sugar3.bundle.activitybundle.ActivityBundle.get_max_participants`
        in :class:`~sugar3.bundle.activitybundle.ActivityBundle`.
        '''
        # If max_participants has not been set in the activity, get it
        # from the bundle.
        if self._max_participants is None:
            bundle = get_bundle_instance(get_bundle_path())
            self._max_participants = bundle.get_max_participants()
        return self._max_participants

    def set_max_participants(self, participants):
        '''
        Set the maximum number of users that can share a instance of
        this activity.  An activity may use this method instead of or
        as well as configuring the activity.info file.  When both are
        used, this method takes precedence over the activity.info
        file.

        Args:
            participants (int): the maximum number of participants
        '''
        self._max_participants = participants

    max_participants = GObject.Property(
        type=int, default=0, getter=get_max_participants,
        setter=set_max_participants)

    def get_id(self):
        '''
        Get the activity id, a likely-unique identifier for the
        instance of an activity, randomly assigned when a new instance
        is started, or read from the journal object metadata when a
        saved instance is resumed.

        Returns:

            str: the activity id

        See also
        :meth:`~sugar3.activity.activityfactory.create_activity_id`
        and :meth:`~sugar3.util.unique_id`.
        '''
        return self._activity_id

    def get_bundle_id(self):
        '''
        Returns:
            int: the bundle_id from the activity.info file
        '''
        return os.environ['SUGAR_BUNDLE_ID']

    def get_canvas(self):
        '''
        Get the :attr:`canvas`.

        Returns:
            :class:`Gtk.Widget`: the widget used as canvas
        '''
        return Window.get_canvas(self)

    def set_canvas(self, canvas):
        '''
        Set the :attr:`canvas`.

        Args:
            canvas (:class:`Gtk.Widget`): the widget used as canvas
        '''

        Window.set_canvas(self, canvas)
        if not self._read_file_called:
            canvas.connect('map', self.__canvas_map_cb)

    canvas = property(get_canvas, set_canvas)
    '''
    The :class:`Gtk.Widget` used as canvas, or work area of your
    activity.  A common canvas is :class:`Gtk.ScrolledWindow`.
    '''

    def __screen_size_changed_cb(self, screen):
        self._adapt_window_to_screen()

    def __window_state_event_cb(self, window, event):
        self.move(0, 0)

    def _adapt_window_to_screen(self):
        screen = Gdk.Screen.get_default()
        rect = screen.get_monitor_geometry(screen.get_number())
        geometry = Gdk.Geometry()
        geometry.max_width = geometry.base_width = geometry.min_width = \
            rect.width
        geometry.max_height = geometry.base_height = geometry.min_height = \
            rect.height
        geometry.width_inc = geometry.height_inc = geometry.min_aspect = \
            geometry.max_aspect = 1
        hints = Gdk.WindowHints(Gdk.WindowHints.ASPECT |
                                Gdk.WindowHints.BASE_SIZE |
                                Gdk.WindowHints.MAX_SIZE |
                                Gdk.WindowHints.MIN_SIZE)
        self.set_geometry_hints(None, geometry, hints)

    def __session_quit_requested_cb(self, session):
        self._quit_requested = True

        if self._prepare_close() and not self._updating_jobject:
            session.will_quit(self, True)

    def __session_quit_cb(self, client):
        self._complete_close()

    def __canvas_map_cb(self, canvas):
        logging.debug('Activity.__canvas_map_cb')
        if self._jobject and self._jobject.file_path and \
                not self._read_file_called:
            self.read_file(self._jobject.file_path)
            self._read_file_called = True
        canvas.disconnect_by_func(self.__canvas_map_cb)

    def __jobject_create_cb(self):
        pass

    def __jobject_error_cb(self, err):
        logging.debug('Error creating activity datastore object: %s' % err)

    def get_activity_root(self):
        '''
        Deprecated. This part of the API has been moved
        out of this class to the module itself
        '''
        return get_activity_root()

    def read_file(self, file_path):
        '''
        Subclasses implement this method if they support resuming objects from
        the journal. 'file_path' is the file to read from.

        You should immediately open the file from the file_path,
        because the file_name will be deleted immediately after
        returning from :meth:`read_file`.

        Once the file has been opened, you do not have to read it immediately:
        After you have opened it, the file will only be really gone when you
        close it.

        Although not required, this is also a good time to read all meta-data:
        the file itself cannot be changed externally, but the title,
        description and other metadata['tags'] may change. So if it is
        important for you to notice changes, this is the time to record the
        originals.

        Args:
            file_path (str): the file path to read
        '''
        raise NotImplementedError

    def write_file(self, file_path):
        '''
        Subclasses implement this method if they support saving data to objects
        in the journal. 'file_path' is the file to write to.

        If the user did make changes, you should create the file_path and save
        all document data to it.

        Additionally, you should also write any metadata needed to resume your
        activity. For example, the Read activity saves the current page and
        zoom level, so it can display the page.

        Note: Currently, the file_path *WILL* be different from the
        one you received in :meth:`read_file`. Even if you kept the
        file_path from :meth:`read_file` open until now, you must
        still write the entire file to this file_path.

        Args:
            file_path (str): complete path of the file to write
        '''
        raise NotImplementedError

    def notify_user(self, summary, body):
        '''
        Display a notification with the given summary and body.
        The notification will go under the activities icon in the frame.
        '''
        bundle = get_bundle_instance(get_bundle_path())
        icon = bundle.get_icon()

        bus = dbus.SessionBus()
        notify_obj = bus.get_object(N_BUS_NAME, N_OBJ_PATH)
        notifications = dbus.Interface(notify_obj, N_IFACE_NAME)

        notifications.Notify(self.get_id(), 0, '', summary, body, [],
                             {'x-sugar-icon-file-name': icon}, -1)

    def __save_cb(self):
        logging.debug('Activity.__save_cb')
        self._updating_jobject = False
        if self._quit_requested:
            self._session.will_quit(self, True)
        elif self._closing:
            self._complete_close()

    def __save_error_cb(self, err):
        logging.debug('Activity.__save_error_cb')
        self._updating_jobject = False
        if self._quit_requested:
            self._session.will_quit(self, False)
        if self._closing:
            self._show_keep_failed_dialog()
            self._closing = False
        raise RuntimeError('Error saving activity object to datastore: %s' %
                           err)

    def _cleanup_jobject(self):
        if self._jobject:
            if self._owns_file and os.path.isfile(self._jobject.file_path):
                logging.debug('_cleanup_jobject: removing %r' %
                              self._jobject.file_path)
                os.remove(self._jobject.file_path)
            self._owns_file = False
            self._jobject.destroy()
            self._jobject = None

    def get_preview(self):
        '''
        Get a preview image from the :attr:`canvas`, for use as
        metadata for the journal object.  This should be what the user
        is seeing at the time.

        Returns:
            str: image data in PNG format

        Activities may override this method, and return a string with
        image data in PNG format with a width and height of
        :attr:`~sugar3.activity.activity.PREVIEW_SIZE` pixels.

        The method creates a Cairo surface similar to that of the
        :ref:`Gdk.Window` of the :meth:`canvas` widget, draws on it,
        then resizes to a surface with the preview size.
        '''
        if self.canvas is None or not hasattr(self.canvas, 'get_window'):
            return None

        window = self.canvas.get_window()
        if window is None:
            return None

        alloc = self.canvas.get_allocation()

        dummy_cr = Gdk.cairo_create(window)
        target = dummy_cr.get_target()
        canvas_width, canvas_height = alloc.width, alloc.height
        screenshot_surface = target.create_similar(cairo.CONTENT_COLOR,
                                                   canvas_width, canvas_height)
        del dummy_cr, target

        cr = cairo.Context(screenshot_surface)
        r, g, b, a_ = style.COLOR_PANEL_GREY.get_rgba()
        cr.set_source_rgb(r, g, b)
        cr.paint()
        self.canvas.draw(cr)
        del cr

        preview_width, preview_height = PREVIEW_SIZE
        preview_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                             preview_width, preview_height)
        cr = cairo.Context(preview_surface)

        scale_w = preview_width * 1.0 / canvas_width
        scale_h = preview_height * 1.0 / canvas_height
        scale = min(scale_w, scale_h)

        translate_x = int((preview_width - (canvas_width * scale)) / 2)
        translate_y = int((preview_height - (canvas_height * scale)) / 2)

        cr.translate(translate_x, translate_y)
        cr.scale(scale, scale)

        cr.set_source_rgba(1, 1, 1, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_source_surface(screenshot_surface)
        cr.paint()

        preview_str = six.BytesIO()
        preview_surface.write_to_png(preview_str)
        return preview_str.getvalue()

    def _get_buddies(self):
        if self.shared_activity is not None:
            buddies = {}
            for buddy in self.shared_activity.get_joined_buddies():
                if not buddy.props.owner:
                    if six.PY2:
                        buddy_id = sha1(buddy.props.key).hexdigest()
                    else:
                        buddy_id = sha1((buddy.props.key).encode('utf-8')).hexdigest()
                    buddies[buddy_id] = [buddy.props.nick, buddy.props.color]
            return buddies
        else:
            return {}

    def save(self):
        '''
        Save to the journal.

        This may be called by the :meth:`close` method.

        Activities should not override this method. This method is part of the
        public API of an activity, and should behave in standard ways. Use your
        own implementation of write_file() to save your activity specific data.
        '''

        if self._jobject is None:
            logging.debug('Cannot save, no journal object.')
            return

        logging.debug('Activity.save: %r' % self._jobject.object_id)

        if self._updating_jobject:
            logging.info('Activity.save: still processing a previous request.')
            return

        buddies_dict = self._get_buddies()
        if buddies_dict:
            self.metadata['buddies_id'] = json.dumps(list(buddies_dict.keys()))
            self.metadata['buddies'] = json.dumps(self._get_buddies())

        # update spent time before saving
        self._update_spent_time()

        def set_last_value(values_list, new_value):
            if ', ' not in values_list:
                return '%d' % new_value
            else:
                partial_list = ', '.join(values_list.split(', ')[:-1])
                return partial_list + ', %d' % new_value

        self.metadata['spent-times'] = set_last_value(
            self.metadata['spent-times'], self._spent_time)

        preview = self.get_preview()
        if preview is not None:
            self.metadata['preview'] = dbus.ByteArray(preview)

        if not self.metadata.get('activity_id', ''):
            self.metadata['activity_id'] = self.get_id()

        file_path = os.path.join(get_activity_root(), 'instance',
                                 '%i' % time.time())
        try:
            self.write_file(file_path)
        except NotImplementedError:
            logging.debug('Activity.write_file is not implemented.')
        else:
            if os.path.exists(file_path):
                self._owns_file = True
                self._jobject.file_path = file_path

        # Cannot call datastore.write async for creates:
        # https://dev.laptop.org/ticket/3071
        if self._jobject.object_id is None:
            datastore.write(self._jobject, transfer_ownership=True)
        else:
            self._updating_jobject = True
            datastore.write(self._jobject,
                            transfer_ownership=True,
                            reply_handler=self.__save_cb,
                            error_handler=self.__save_error_cb)

    def copy(self):
        '''
        Make a copy of the journal object.

        Activities may use this to 'Keep in Journal' the current state
        of the activity.  A new journal object will be created for the
        running activity.

        Activities should not override this method. Instead, like
        :meth:`save` do any copy work that needs to be done in
        :meth:`write_file`.
        '''
        logging.debug('Activity.copy: %r' % self._jobject.object_id)
        self.save()
        self._jobject.object_id = None

    def __privacy_changed_cb(self, shared_activity, param_spec):
        logging.debug('__privacy_changed_cb %r' %
                      shared_activity.props.private)
        if shared_activity.props.private:
            self._jobject.metadata['share-scope'] = SCOPE_INVITE_ONLY
        else:
            self._jobject.metadata['share-scope'] = SCOPE_NEIGHBORHOOD

    def __joined_cb(self, activity, success, err):
        """Callback when join has finished"""
        logging.debug('Activity.__joined_cb %r' % success)
        self.shared_activity.disconnect(self._join_id)
        self._join_id = None
        if not success:
            logging.debug('Failed to join activity: %s' % err)
            return

        power_manager = power.get_power_manager()
        if power_manager.suspend_breaks_collaboration():
            power_manager.inhibit_suspend()

        self.reveal()
        self.emit('joined')
        self.__privacy_changed_cb(self.shared_activity, None)

    def get_shared_activity(self):
        '''
        Get the shared activity of type
        :class:`sugar3.presence.activity.Activity`, or None if the
        activity is not shared, or is shared and not yet joined.

        Returns:
            :class:`sugar3.presence.activity.Activity`: instance of
                the shared activity or None
        '''
        return self.shared_activity

    def get_shared(self):
        '''
        Get whether the activity is shared.

        Returns:
            bool: the activity is shared.
        '''
        if not self.shared_activity:
            return False
        return self.shared_activity.props.joined

    def __share_cb(self, ps, success, activity, err):
        if not success:
            logging.debug('Share of activity %s failed: %s.' %
                          (self._activity_id, err))
            return

        logging.debug('Share of activity %s successful, PS activity is %r.' %
                      (self._activity_id, activity))

        activity.props.name = self._jobject.metadata['title']

        power_manager = power.get_power_manager()
        if power_manager.suspend_breaks_collaboration():
            power_manager.inhibit_suspend()

        self.shared_activity = activity
        self.shared_activity.connect('notify::private',
                                     self.__privacy_changed_cb)
        self.emit('shared')
        self.__privacy_changed_cb(self.shared_activity, None)

        self._send_invites()

    def _invite_response_cb(self, error):
        if error:
            logging.error('Invite failed: %s', error)

    def _send_invites(self):
        while self._invites_queue:
            account_path, contact_id = self._invites_queue.pop()
            pservice = presenceservice.get_instance()
            buddy = pservice.get_buddy(account_path, contact_id)
            if buddy:
                self.shared_activity.invite(
                    buddy, '', self._invite_response_cb)
            else:
                logging.error('Cannot invite %s %s, no such buddy',
                              account_path, contact_id)

    def invite(self, account_path, contact_id):
        '''
        Invite a buddy to join this activity.

        Args:
            account_path
            contact_id

        **Side Effects:**
            Calls :meth:`share` to privately share the activity if it wasn't
            shared before.
        '''
        self._invites_queue.append((account_path, contact_id))

        if (self.shared_activity is None or
                not self.shared_activity.props.joined):
            self.share(True)
        else:
            self._send_invites()

    def share(self, private=False):
        '''
        Request that the activity be shared on the network.

        Args:
            private (bool): True to share by invitation only,
                False to advertise as shared to everyone.

        Once the activity is shared, its privacy can be changed by
        setting the :attr:`private` property of the
        :attr:`sugar3.presence.activity.Activity` class.
        '''
        if self.shared_activity and self.shared_activity.props.joined:
            raise RuntimeError('Activity %s already shared.' %
                               self._activity_id)
        verb = private and 'private' or 'public'
        logging.debug(
            'Requesting %s share of activity %s.' %
            (verb, self._activity_id))
        pservice = presenceservice.get_instance()
        pservice.connect('activity-shared', self.__share_cb)
        pservice.share_activity(self, private=private)

    def _show_keep_failed_dialog(self):
        '''
        A keep error means the activity write_file method raised an
        exception before writing the file, or the datastore cannot be
        written to.
        '''
        alert = Alert()
        alert.props.title = _('Keep error')
        alert.props.msg = _('Keep error: all changes will be lost')

        cancel_icon = Icon(icon_name='dialog-cancel')
        alert.add_button(Gtk.ResponseType.CANCEL, _('Don\'t stop'),
                         cancel_icon)

        stop_icon = Icon(icon_name='dialog-ok')
        alert.add_button(Gtk.ResponseType.OK, _('Stop anyway'), stop_icon)

        self.add_alert(alert)
        alert.connect('response', self.__keep_failed_dialog_response_cb)

        self.reveal()

    def __keep_failed_dialog_response_cb(self, alert, response_id):
        self.remove_alert(alert)
        if response_id == Gtk.ResponseType.OK:
            self.close(skip_save=True)
            if self._quit_requested:
                self._session.will_quit(self, True)
        elif self._quit_requested:
            self._session.will_quit(self, False)

    def can_close(self):
        '''
        Return whether :func:`close` is permitted.

        An activity may override this function to code extra checks
        before closing.

        Returns:
            bool: whether :func:`close` is permitted by activity,
            default True.
        '''

        return True

    def _show_stop_dialog(self):
        for button in self._stop_buttons:
            button.set_sensitive(False)
        alert = Alert()
        alert.props.title = _('Stop')
        alert.props.msg = _('Stop: name your journal entry')

        title = self._jobject.metadata['title']
        alert.entry = alert.add_entry()
        alert.entry.set_text(title)

        label, tip = self._get_save_label_tip(title)
        button = alert.add_button(Gtk.ResponseType.OK, label,
                                  Icon(icon_name='dialog-ok'))
        button.add_accelerator('clicked', self.sugar_accel_group,
                               Gdk.KEY_Return, 0, 0)
        button.set_tooltip_text(tip)
        alert.ok = button

        label, tip = self._get_erase_label_tip()
        button = alert.add_button(Gtk.ResponseType.ACCEPT, label,
                                  Icon(icon_name='list-remove'))
        button.set_tooltip_text(tip)

        button = alert.add_button(Gtk.ResponseType.CANCEL, _('Cancel'),
                                  Icon(icon_name='dialog-cancel'))
        button.add_accelerator('clicked', self.sugar_accel_group,
                               Gdk.KEY_Escape, 0, 0)
        button.set_tooltip_text(_('Cancel stop and continue the activity'))

        alert.connect('realize', self.__stop_dialog_realize_cb)
        alert.connect('response', self.__stop_dialog_response_cb)
        alert.entry.connect('changed', self.__stop_dialog_changed_cb, alert)
        self.add_alert(alert)
        alert.show()

    def __stop_dialog_realize_cb(self, alert):
        alert.entry.grab_focus()

    def __stop_dialog_response_cb(self, alert, response_id):
        if response_id == Gtk.ResponseType.OK:
            title = alert.entry.get_text()
            if self._is_resumed and \
                    title == self._original_title:
                datastore.delete(self._jobject_old.get_object_id())
            self._jobject.metadata['title'] = title
            self._do_close(False)

        if response_id == Gtk.ResponseType.ACCEPT:
            datastore.delete(self._jobject.get_object_id())
            self._do_close(True)

        if response_id == Gtk.ResponseType.CANCEL:
            for button in self._stop_buttons:
                button.set_sensitive(True)

        self.remove_alert(alert)

    def __stop_dialog_changed_cb(self, entry, alert):
        label, tip = self._get_save_label_tip(entry.get_text())

        alert.ok.set_label(label)
        alert.ok.set_tooltip_text(tip)

    def _get_save_label_tip(self, title):
        label = _('Save new')
        tip = _('Save a new journal entry')
        if self._is_resumed and \
                title == self._original_title:
            label = _('Save')
            tip = _('Save into the old journal entry')

        return label, tip

    def _get_erase_label_tip(self):
        if self._is_resumed:
            label = _('Erase changes')
            tip = _('Erase what you have done, '
                    'and leave your old journal entry unchanged')
        else:
            label = _('Erase')
            tip = _('Erase what you have done, '
                    'and avoid making a journal entry')

        return label, tip

    def _prepare_close(self, skip_save=False):
        if not skip_save:
            try:
                self.save()
            except BaseException:
                # pylint: disable=W0702
                logging.exception('Error saving activity object to datastore')
                self._show_keep_failed_dialog()
                return False

        self._closing = True

        return True

    def _complete_close(self):
        self.destroy()

        if self.shared_activity:
            self.shared_activity.leave()

        self._cleanup_jobject()

        # Make the exported object inaccessible
        dbus.service.Object.remove_from_connection(self._bus)

        self._session.unregister(self)
        power.get_power_manager().shutdown()

    def _do_close(self, skip_save):
        self.busy()
        self.emit('_closing')
        if not self._closing:
            if not self._prepare_close(skip_save):
                return

        if not self._updating_jobject:
            self._complete_close()

    def close(self, skip_save=False):
        '''
        Save to the journal and stop the activity.

        Activities should not override this method, but should
        implement :meth:`write_file` to do any state saving
        instead. If the activity wants to control wether it can close,
        it should override :meth:`can_close`.

        Args:
            skip_save (bool): avoid last-chance save; but does not prevent
                a journal object, as an object is created when the activity
                starts.  Use this when an activity calls :meth:`save` just
                prior to :meth:`close`.
        '''
        if not self.can_close():
            return

        if get_save_as():
            if self._jobject.metadata['title'] != self._original_title:
                self._do_close(skip_save)
            else:
                self._show_stop_dialog()
        else:
            self._do_close(skip_save)

    def __realize_cb(self, window):
        display_name = Gdk.Display.get_default().get_name()
        if ':' in display_name:
            # X11 for sure; this only works in X11
            xid = window.get_window().get_xid()
            SugarExt.wm_set_bundle_id(xid, self.get_bundle_id())
            SugarExt.wm_set_activity_id(xid, str(self._activity_id))
        elif display_name is 'Broadway':
            # GTK3's HTML5 backend
            # This is needed so that the window takes the whole browser window
            self.maximize()

    def __delete_event_cb(self, widget, event):
        self.close()
        return True

    def get_metadata(self):
        '''
        Get the journal object metadata.

        Returns:

            dict: the journal object metadata, or None if there is no object.

        Activities can set metadata in write_file() using:

        .. code-block:: python

            self.metadata['MyKey'] = 'Something'

        and retrieve metadata in read_file() using:

        .. code-block:: python

            self.metadata.get('MyKey', 'aDefaultValue')

        Make sure your activity works properly if one or more of the
        metadata items is missing. Never assume they will all be
        present.
        '''
        if self._jobject:
            return self._jobject.metadata
        else:
            return None

    metadata = property(get_metadata, None)

    def handle_view_source(self):
        '''
        An activity may override this method to show aditional
        information in the View Source window. Examples can be seen in
        Browse and TurtleArt.

        Raises:
            :exc:`NotImplementedError`
        '''
        raise NotImplementedError

    def get_document_path(self, async_cb, async_err_cb):
        '''
        Not implemented.
        '''
        async_err_cb(NotImplementedError())

    def busy(self):
        '''
        Show that the activity is busy.  If used, must be called once
        before a lengthy operation, and :meth:`unbusy` must be called
        after the operation completes.

        .. code-block:: python

            self.busy()
            self.long_operation()
            self.unbusy()
        '''
        if self._busy_count == 0:
            self._old_cursor = self.get_window().get_cursor()
            self._set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        self._busy_count += 1

    def unbusy(self):
        '''
        Show that the activity is not busy.  An equal number of calls
        to :meth:`unbusy` are required to balance the calls to
        :meth:`busy`.

        Returns:
            int: a count of further calls to :meth:`unbusy` expected
        '''
        self._busy_count -= 1
        if self._busy_count == 0:
            self._set_cursor(self._old_cursor)
        return self._busy_count

    def _set_cursor(self, cursor):
        self.get_window().set_cursor(cursor)
        Gdk.flush()


class _ClientHandler(dbus.service.Object):
    def __init__(self, bundle_id, got_channel_cb):
        self._interfaces = set([CLIENT, CLIENT_HANDLER, PROPERTIES_IFACE])
        self._got_channel_cb = got_channel_cb

        bus = dbus.Bus()
        name = CLIENT + '.' + bundle_id
        bus_name = dbus.service.BusName(name, bus=bus)

        path = '/' + name.replace('.', '/')
        dbus.service.Object.__init__(self, bus_name, path)

        self._prop_getters = {}
        self._prop_setters = {}
        self._prop_getters.setdefault(CLIENT, {}).update({
            'Interfaces': lambda: list(self._interfaces),
        })
        self._prop_getters.setdefault(CLIENT_HANDLER, {}).update({
            'HandlerChannelFilter': self.__get_filters_cb,
        })

    def __get_filters_cb(self):
        logging.debug('__get_filters_cb')
        filters = {
            CHANNEL + '.ChannelType': CHANNEL_TYPE_TEXT,
            CHANNEL + '.TargetHandleType': CONNECTION_HANDLE_TYPE_CONTACT,
        }
        filter_dict = dbus.Dictionary(filters, signature='sv')
        logging.debug('__get_filters_cb %r' % dbus.Array([filter_dict],
                                                         signature='a{sv}'))
        return dbus.Array([filter_dict], signature='a{sv}')

    @dbus.service.method(dbus_interface=CLIENT_HANDLER,
                         in_signature='ooa(oa{sv})aota{sv}', out_signature='')
    def HandleChannels(self, account, connection, channels, requests_satisfied,
                       user_action_time, handler_info):
        logging.debug('HandleChannels\n\t%r\n\t%r\n\t%r\n\t%r\n\t%r\n\t%r' %
                      (account, connection, channels, requests_satisfied,
                          user_action_time, handler_info))
        try:
            for object_path, properties in channels:
                channel_type = properties[CHANNEL + '.ChannelType']
                handle_type = properties[CHANNEL + '.TargetHandleType']
                if channel_type == CHANNEL_TYPE_TEXT:
                    self._got_channel_cb(connection, object_path, handle_type)
        except Exception as e:
            logging.exception(e)

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        if interface_name in self._prop_getters \
           and property_name in self._prop_getters[interface_name]:
                return self._prop_getters[interface_name][property_name]()
        else:
            logging.debug('InvalidArgument')

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ssv', out_signature='')
    def Set(self, interface_name, property_name, value):
        if interface_name in self._prop_setters \
           and property_name in self._prop_setters[interface_name]:
                self._prop_setters[interface_name][property_name](value)
        else:
            logging.debug('PermissionDenied')

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        if interface_name in self._prop_getters:
            r = {}
            for k, v in list(self._prop_getters[interface_name].items()):
                r[k] = v()
            return r
        else:
            logging.debug('InvalidArgument')


_session = None


def _get_session():
    global _session

    if _session is None:
        _session = _ActivitySession()

    return _session


def get_bundle_name():
    '''
    Returns:
        str: the bundle name for the current process' bundle
    '''
    return os.environ['SUGAR_BUNDLE_NAME']


def get_bundle_path():
    '''
    Returns:
        str: the bundle path for the current process' bundle
    '''
    return os.environ['SUGAR_BUNDLE_PATH']


def get_activity_root():
    '''
    Returns:
        str: a path for saving Activity specific preferences, etc.

    Returns a path to the location in the filesystem where the
    activity can store activity related data that doesn't pertain to
    the current execution of the activity and thus cannot go into the
    DataStore.

    Currently, this will return something like
    ~/.sugar/default/MyActivityName/

    Activities should ONLY save settings, user preferences and other
    data which isn't specific to a journal item here. If (meta-)data
    is in anyway specific to a journal entry, it MUST be stored in the
    DataStore.
    '''
    if os.environ.get('SUGAR_ACTIVITY_ROOT'):
        return os.environ['SUGAR_ACTIVITY_ROOT']
    else:
        activity_root = env.get_profile_path(os.environ['SUGAR_BUNDLE_ID'])
        try:
            os.mkdir(activity_root)
        except OSError as e:
            if e.errno != EEXIST:
                raise e
        return activity_root


def show_object_in_journal(object_id):
    '''
    Raise the journal activity and show a journal object.

    Args:
        object_id (object): journal object
    '''
    bus = dbus.SessionBus()
    obj = bus.get_object(J_DBUS_SERVICE, J_DBUS_PATH)
    journal = dbus.Interface(obj, J_DBUS_INTERFACE)
    journal.ShowObject(object_id)


def launch_bundle(bundle_id='', object_id=''):
    '''
    Launch an activity for a journal object, or an activity.

    Args:
        bundle_id (str): activity bundle id, optional
        object_id (object): journal object
    '''
    bus = dbus.SessionBus()
    obj = bus.get_object(J_DBUS_SERVICE, J_DBUS_PATH)
    bundle_launcher = dbus.Interface(obj, J_DBUS_INTERFACE)
    return bundle_launcher.LaunchBundle(bundle_id, object_id)


def get_bundle(bundle_id='', object_id=''):
    '''
    Get the bundle id of an activity that can open a journal object.

    Args:
        bundle_id (str): activity bundle id, optional
        object_id (object): journal object
    '''
    bus = dbus.SessionBus()
    obj = bus.get_object(J_DBUS_SERVICE, J_DBUS_PATH)
    journal = dbus.Interface(obj, J_DBUS_INTERFACE)
    bundle_path = journal.GetBundlePath(bundle_id, object_id)
    if bundle_path:
        return bundle_from_dir(bundle_path)
    else:
        return None

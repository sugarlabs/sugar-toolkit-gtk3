'''
Base class for activities written in Python
===========================================

This is currently the only definitive reference for what an
activity must do to participate in the Sugar desktop.

A Basic Activity
----------------

All activities must implement a class derived from 'Activity' in this class.
The convention is to call it ActivitynameActivity, but this is not required as
the activity.info file associated with your activity will tell the sugar-shell
which class to start.

For example the most minimal Activity:

.. code-block:: python

   from sugar3.activity import activity

   class ReadActivity(activity.Activity):
        pass

To get a real, working activity, you will at least have to implement:

__init__(), :func:`sugar3.activity.activity.Activity.read_file()` and
:func:`sugar3.activity.activity.Activity.write_file()`

Aditionally, you will probably need a at least a Toolbar so you can have some
interesting buttons for the user, like for example 'exit activity'

See the methods of the Activity class below for more information on what you
will need for a real activity.

.. note:: This API is STABLE.
'''
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

import gettext
import logging
import os
import time
from hashlib import sha1
from functools import partial
import StringIO
import cairo
import json

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('SugarExt', '1.0')

from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import Gtk
import dbus
import dbus.service
from dbus import PROPERTIES_IFACE
from telepathy.server import DBusProperties
from telepathy.interfaces import CHANNEL, \
    CHANNEL_TYPE_TEXT, \
    CLIENT, \
    CLIENT_HANDLER
from telepathy.constants import CONNECTION_HANDLE_TYPE_CONTACT
from telepathy.constants import CONNECTION_HANDLE_TYPE_ROOM

from sugar3 import util
from sugar3 import power
from sugar3.profile import get_nick_name, get_color, get_save_as
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

_ = lambda msg: gettext.dgettext('sugar-toolkit-gtk3', msg)

SCOPE_PRIVATE = 'private'
SCOPE_INVITE_ONLY = 'invite'  # shouldn't be shown in UI, it's implicit
SCOPE_NEIGHBORHOOD = 'public'

J_DBUS_SERVICE = 'org.laptop.Journal'
J_DBUS_PATH = '/org/laptop/Journal'
J_DBUS_INTERFACE = 'org.laptop.Journal'

N_BUS_NAME = 'org.freedesktop.Notifications'
N_OBJ_PATH = '/org/freedesktop/Notifications'
N_IFACE_NAME = 'org.freedesktop.Notifications'

CONN_INTERFACE_ACTIVITY_PROPERTIES = 'org.laptop.Telepathy.ActivityProperties'

PREVIEW_SIZE = style.zoom(300), style.zoom(225)


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
    '''
    This is the base Activity class that all other Activities derive from.
    This is where your activity starts.

    To get a working Activity:
        0. Derive your Activity from this class:

        .. code-block:: python

            class MyActivity(activity.Activity):
                ...

        1. implement an __init__() method for your Activity class.

        Use your init method to create your own ToolbarBox.
        This is the code to make a basic toolbar with the activity
        toolbar and a stop button.

        .. code-block:: python

            from sugar3.graphics.toolbarbox import ToolbarBox
            from sugar3.activity.widgets import ActivityToolbarButton
            from sugar3.activity.widgets import StopButton

            def __init__(self, handle):
                activity.Activity.__init__(self, handle)

                toolbar_box = ToolbarBox()
                activity_button = ActivityToolbarButton(self)
                toolbar_box.toolbar.insert(activity_button, 0)
                activity_button.show()

                ... Your toolbars ...

                separator = Gtk.SeparatorToolItem(draw=False)
                separator.set_expand(True)
                toolbar_box.toolbar.insert(separator, -1)
                separator.show()

                stop_button = StopButton(self)
                toolbar_box.toolbar.insert(stop_button, -1)
                stop_button.show()

                self.set_toolbar_box(toolbar_box)
                toolbar_box.show()

        Add extra Toolbars to your toolbox.

        You should setup Activity sharing here too.

        Finaly, your Activity may need some resources which you can claim
        here too.

        The __init__() method is also used to make the distinction between
        being resumed from the Journal, or starting with a blank document.

        2. Implement :func:`sugar3.activity.activity.Activity.read_file()` and
        :func:`sugar3.activity.activity.Activity.write_file()`
        Most activities revolve around creating and storing Journal entries.
        For example, Write: You create a document, it is saved to the
        Journal and then later you resume working on the document.

        :func:`sugar3.activity.activity.Activity.read_file()` and
        :func:`sugar3.activity.activity.Activity.write_file()`
        will be called by sugar to tell your
        Activity that it should load or save the document the user is
        working on.

        3. Implement our Activity Toolbars.

        The Toolbars are added to your Activity in step 1 (the toolbox), but
        you need to implement them somewhere. Now is a good time.

        There are a number of standard Toolbars. The most basic one, the one
        your almost absolutely MUST have is the ActivityToolbar. Without
        this, you're not really making a proper Sugar Activity (which may be
        okay, but you should really stop and think about why not!) You do
        this with the ActivityToolbox(self) call in step 1.

        Usually, you will also need the standard EditToolbar. This is the
        one which has the standard copy and paste buttons. You need to
        derive your own EditToolbar class from
        :class:`sugar3.activity.widgets.EditToolbar`:

        .. code-block:: python

            from sugar3.activity.widgets import EditToolbar

            class MyEditToolbar(EditToolbar):
                ...

        See EditToolbar for the methods you should implement in your class.

        Finaly, your Activity will very likely need some activity specific
        buttons and options you can create your own toolbars by deriving a
        class from :class:`Gtk.Toolbar`:

        .. code-block:: python

            class MySpecialToolbar(Gtk.Toolbar):
            ...

        4. Use your creativity. Make your Activity something special and share
           it with your friends!

        Read through the methods of the Activity class below, to learn more
        about how to make an Activity work.

        Hint: A good and simple Activity to learn from is the Read activity.
        To create your own activity, you may want to copy it and use it as a
        template.
    '''

    __gtype_name__ = 'SugarActivity'

    __gsignals__ = {
        'shared': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'joined': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        # For internal use only, use can_close() if you want to perform extra
        # checks before actually closing
        '_closing': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, handle, create_jobject=True):
        '''
        Initialise the Activity

        Args:

        handle (sugar3.activity.activityhandle.ActivityHandle)
            instance providing the activity id and access to the
            presence service which *may* provide sharing for this
            application
        create_jobject (boolean)
            DEPRECATED: define if it should create a journal object if we are
            not resuming. The parameter is ignored, and always  will
            be created a object in the Journal.

        Side effects:

            Sets the gdk screen DPI setting (resolution) to the
            Sugar screen resolution.

            Connects our "destroy" message to our _destroy_cb
            method.

            Creates a base Gtk.Window within this window.

            Creates an ActivityService (self._bus) servicing
            this application.

        Usage:
            If your Activity implements __init__(), it should call
            the base class __init()__ before doing Activity specific things.

        '''

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
        self._stop_buttons.append(button)

    def run_main_loop(self):
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
        if self._active != active:
            self._active = active
            self._update_spent_time()
            if not self._active and self._jobject:
                self.save()

    active = GObject.property(
        type=bool, default=False, getter=get_active, setter=set_active)

    def get_max_participants(self):
        '''
        Returns:
            int: the max number of users than can share a instance of the
            activity. Should be configured in the activity.info file.
        '''
        # If max_participants has not been set in the activity, get it
        # from the bundle.
        if self._max_participants is None:
            bundle = get_bundle_instance(get_bundle_path())
            self._max_participants = bundle.get_max_participants()
        return self._max_participants

    def set_max_participants(self, participants):
        self._max_participants = participants

    max_participants = GObject.property(
        type=int, default=0, getter=get_max_participants,
        setter=set_max_participants)

    def get_id(self):
        '''
        Returns:

            int: the activity id of the current instance of your activity.

            The activity id is sort-of-like the unix process id (PID). However,
            unlike PIDs it is only different for each new instance
            and stays the same everytime a user
            resumes an activity. This is also the identity of your Activity to
            other XOs for use when sharing.
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
        Returns:
            :class:`Gtk.Widget`: the widget used as canvas
        '''
        return Window.get_canvas(self)

    def set_canvas(self, canvas):
        '''
        Sets the 'work area' of your activity with the canvas of your choice.

        One commonly used canvas is Gtk.ScrolledWindow

        Args:
            canvas (:class:`Gtk.Widget`): the widget used as canvas
        '''

        Window.set_canvas(self, canvas)
        if not self._read_file_called:
            canvas.connect('map', self.__canvas_map_cb)

    canvas = property(get_canvas, set_canvas)

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

        Returns:
            str: a path for saving Activity specific preferences, etc.

        Returns a path to the location in the filesystem where the activity can
        store activity related data that doesn't pertain to the current
        execution of the activity and thus cannot go into the DataStore.

        Currently, this will return something like
        ~/.sugar/default/MyActivityName/

        Activities should ONLY save settings, user preferences and other data
        which isn't specific to a journal item here. If (meta-)data is in
        anyway specific to a journal entry, it MUST be stored in the DataStore.
        '''
        if os.environ.get('SUGAR_ACTIVITY_ROOT'):
            return os.environ['SUGAR_ACTIVITY_ROOT']
        else:
            return get_activity_root()

    def read_file(self, file_path):
        '''
        Subclasses implement this method if they support resuming objects from
        the journal. 'file_path' is the file to read from.

        You should immediately open the file from the file_path, because the
        file_name will be deleted immediately after returning from read_file().
        Once the file has been opened, you do not have to read it immediately:
        After you have opened it, the file will only be really gone when you
        close it.

        Although not required, this is also a good time to read all meta-data:
        the file itself cannot be changed externally, but the title,
        description and other metadata['tags'] may change. So if it is
        important for you to notice changes, this is the time to record the
        originals.

        Args:
            str: the file path to read
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

        Note: Currently, the file_path *WILL* be different from the one you
        received in file_read(). Even if you kept the file_path from
        file_read() open until now, you must still write the entire file to
        this file_path.

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
        Returns:
            str: with data ready to save with an image representing the state
            of the activity. Generally this is what the user is seeing in
            this moment.

        Activities can override this method, which should return a str with the
        binary content of a png image with a width of PREVIEW_SIZE pixels.

        The method does create a cairo surface similar to that of the canvas'
        window and draws on that. Then we create a cairo image surface with
        the desired preview size and scale the canvas surface on that.
        '''
        if self.canvas is None or not hasattr(self.canvas, 'get_window'):
            return None

        window = self.canvas.get_window()
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

        preview_str = StringIO.StringIO()
        preview_surface.write_to_png(preview_str)
        return preview_str.getvalue()

    def _get_buddies(self):
        if self.shared_activity is not None:
            buddies = {}
            for buddy in self.shared_activity.get_joined_buddies():
                if not buddy.props.owner:
                    buddy_id = sha1(buddy.props.key).hexdigest()
                    buddies[buddy_id] = [buddy.props.nick, buddy.props.color]
            return buddies
        else:
            return {}

    def save(self):
        '''
        Request that the activity is saved to the Journal.

        This method is called by the close() method below. In general,
        activities should not override this method. This method is part of the
        public API of an Activity, and should behave in standard ways. Use your
        own implementation of write_file() to save your Activity specific data.
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
            self.metadata['buddies_id'] = json.dumps(buddies_dict.keys())
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
        Request that the activity 'Keep in Journal' the current state
        of the activity.

        Activities should not override this method. Instead, like save() do any
        copy work that needs to be done in write_file()
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
        Returns:
            an instance of the shared Activity or None

        The shared activity is of type sugar3.presence.activity.Activity
        '''
        return self.shared_activity

    def get_shared(self):
        '''
        Returns:
             bool: True if the activity is shared on the mesh.
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
        Invite a buddy to join this Activity.

        Args:
            account_path
            contact_id

        Side Effects:
            Calls self.share(True) to privately share the activity if it wasn't
            shared before.
        '''
        self._invites_queue.append((account_path, contact_id))

        if (self.shared_activity is None
                or not self.shared_activity.props.joined):
            self.share(True)
        else:
            self._send_invites()

    def share(self, private=False):
        '''
        Request that the activity be shared on the network.

        Args:
            private (bool): True to share by invitation only,
            False to advertise as shared to everyone.

        Once the activity is shared, its privacy can be changed by setting
        its 'private' property.
        '''
        if self.shared_activity and self.shared_activity.props.joined:
            raise RuntimeError('Activity %s already shared.' %
                               self._activity_id)
        verb = private and 'private' or 'public'
        logging.debug('Requesting %s share of activity %s.' % (verb,
                      self._activity_id))
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
        Activities should override this function if they want to perform
        extra checks before actually closing.
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
        # FIXME: does not work with Write activity
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
            except:
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
        Request that the activity be stopped and saved to the Journal

        Activities should not override this method, but should implement
        write_file() to do any state saving instead. If the application wants
        to control wether it can close, it should override can_close().

        Args:
            skip_save (bool)
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
        Returns:

            dict: the jobject metadata or None if there is no jobject.

        Activities can set metadata in write_file() using:

        .. code-block:: python

            self.metadata['MyKey'] = 'Something'

        and retrieve metadata in read_file() using:

        .. code-block:: python

            self.metadata.get('MyKey', 'aDefaultValue')

        Note: Make sure your activity works properly if one or more of the
        metadata items is missing. Never assume they will all be present.
        '''
        if self._jobject:
            return self._jobject.metadata
        else:
            return None

    metadata = property(get_metadata, None)

    def handle_view_source(self):
        '''
        A developer can impleement this method to show aditional information
        in the View Source window. Example implementations are available
        on activities Browse or TurtleArt.
        '''
        raise NotImplementedError

    def get_document_path(self, async_cb, async_err_cb):
        async_err_cb(NotImplementedError())

    def busy(self):
        '''
        Show that the activity is busy.  If used, must be called once
        before a lengthy operation, and unbusy must be called after
        the operation completes.

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
        Returns:

            int: a count of further calls to unbusy expected

        Show that the activity is not busy.  An equal number of calls
        to unbusy are required to balance the calls to busy.
        '''
        self._busy_count -= 1
        if self._busy_count == 0:
            self._set_cursor(self._old_cursor)
        return self._busy_count

    def _set_cursor(self, cursor):
        self.get_window().set_cursor(cursor)
        Gdk.flush()


class _ClientHandler(dbus.service.Object, DBusProperties):
    def __init__(self, bundle_id, got_channel_cb):
        self._interfaces = set([CLIENT, CLIENT_HANDLER, PROPERTIES_IFACE])
        self._got_channel_cb = got_channel_cb

        bus = dbus.Bus()
        name = CLIENT + '.' + bundle_id
        bus_name = dbus.service.BusName(name, bus=bus)

        path = '/' + name.replace('.', '/')
        dbus.service.Object.__init__(self, bus_name, path)
        DBusProperties.__init__(self)

        self._implement_property_get(CLIENT, {
            'Interfaces': lambda: list(self._interfaces),
        })
        self._implement_property_get(CLIENT_HANDLER, {
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
        except Exception, e:
            logging.exception(e)

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
    '''
    if os.environ.get('SUGAR_ACTIVITY_ROOT'):
        return os.environ['SUGAR_ACTIVITY_ROOT']
    else:
        activity_root = env.get_profile_path(os.environ['SUGAR_BUNDLE_ID'])
        try:
            os.mkdir(activity_root)
        except OSError, e:
            if e.errno != EEXIST:
                raise e
        return activity_root


def show_object_in_journal(object_id):
    bus = dbus.SessionBus()
    obj = bus.get_object(J_DBUS_SERVICE, J_DBUS_PATH)
    journal = dbus.Interface(obj, J_DBUS_INTERFACE)
    journal.ShowObject(object_id)


def launch_bundle(bundle_id='', object_id=''):
    bus = dbus.SessionBus()
    obj = bus.get_object(J_DBUS_SERVICE, J_DBUS_PATH)
    bundle_launcher = dbus.Interface(obj, J_DBUS_INTERFACE)
    return bundle_launcher.LaunchBundle(bundle_id, object_id)


def get_bundle(bundle_id='', object_id=''):
    bus = dbus.SessionBus()
    obj = bus.get_object(J_DBUS_SERVICE, J_DBUS_PATH)
    journal = dbus.Interface(obj, J_DBUS_INTERFACE)
    bundle_path = journal.GetBundlePath(bundle_id, object_id)
    if bundle_path:
        return bundle_from_dir(bundle_path)
    else:
        return None

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

# Use 'import gi' instead of individual 'gi.require_version' calls
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('TelepathyGLib', '0.12')
gi.require_version('SugarExt', '1.0')

# Import only necessary modules from gi.repository
from gi.repository import GLib, GObject, Gdk, Gtk, TelepathyGLib
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

# No need to import SugarExt separately, it's already included in gi.repository

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

# Class _ActivitySession remains the same for GTK 4

class Activity(Window, Gtk.Container):
    """
    Initialise an Activity.
    (Remaining docstring omitted for brevity)

    """
    __gtype_name__ = 'SugarActivity'

    __gsignals__ = {
        'shared': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'joined': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'closing': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, handle, create_jobject=True):
        if hasattr(GLib, 'unix_signal_add'):
            GLib.unix_signal_add(
                GLib.PRIORITY_DEFAULT, signal.SIGINT, self.close)

        icons_path = os.path.join(get_bundle_path(), 'icons')
        Gtk.IconTheme.get_default().append_search_path(icons_path)

        sugar_theme = 'sugar-72'
        if 'SUGAR_SCALING' in os.environ:
            if os.environ['SUGAR_SCALING'] == '100':
                sugar_theme = 'sugar-100'

        settings = Gtk.Settings.get_default()
        settings.set_property('gtk-theme-name', sugar_theme)
        settings.set_property('gtk-icon-theme-name', 'sugar')
        settings.set_property('gtk-button-images', True)
        settings.set_property('gtk-font-name',
                              f'{style.FONT_FACE} {style.FONT_SIZE}')

        Window.__init__(self)

        if 'SUGAR_ACTIVITY_ROOT' in os.environ:
            self.connect('window-state-event', self.__window_state_event_cb)
            screen = Gdk.Screen.get_default()
            screen.connect('size-changed', self.__screen_size_changed_cb)
            self._adapt_window_to_screen()

        proc_title = f'{get_bundle_name()} <{handle.activity_id}>'
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
                self._jobject.metadata['launch-times'] += f', {int(time.time())}'
            else:
                self._jobject.metadata['launch-times'] = str(int(time.time()))

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
            self._jobject_old = self._jobject
            self._jobject = datastore.copy(self._jobject, '/')

        self._original_title = self._jobject.metadata['title']

    def add_stop_button(self, button):
        self._stop_buttons.append(button)

    def iconify(self):
        if not self._in_main:
            self._iconify = True
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
        if self.get_title() == jobject.metadata['title']:
            return
        self.set_title(jobject.metadata['title'])

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
        rect = screen.get_monitor_geometry(screen.get_primary_monitor())
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
            bytes: image data in PNG format

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
        screenshot_surface = target.create_similar(cairo.Content.COLOR,
                                                   canvas_width, canvas_height)
        del dummy_cr, target

        cr = cairo.Context(screenshot_surface)
        r, g, b, a_ = style.COLOR_PANEL_GREY.get_rgba()
        cr.set_source_rgb(r, g, b)
        cr.paint()
        self.canvas.draw(cr)
        del cr

        preview_width, preview_height = PREVIEW_SIZE
        preview_surface = cairo.ImageSurface(cairo.Format.ARGB32,preview_width, preview_height)
        cr = cairo.Context(preview_surface)

        scale_w = preview_width * 1.0 / canvas_width
        scale_h = preview_height * 1.0 / canvas_height
        scale = min(scale_w, scale_h)

        translate_x = int((preview_width - (canvas_width * scale)) / 2)
        translate_y = int((preview_height - (canvas_height * scale)) / 2)

        cr.translate(translate_x, translate_y)
        cr.scale(scale, scale)

        cr.set_source_rgba(1, 1, 1, 0)
        cr.set_operator(cairo.Operator.SOURCE)
        cr.paint()
        cr.set_source_surface(screenshot_surface)
        cr.paint()

        preview_str = BytesIO()
        preview_surface.write_to_png(preview_str)
        return preview_str.getvalue()




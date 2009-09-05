"""Base class for activities written in Python

This is currently the only definitive reference for what an
activity must do to participate in the Sugar desktop.

   A Basic Activity

All activities must implement a class derived from 'Activity' in this class.
The convention is to call it ActivitynameActivity, but this is not required as
the activity.info file associated with your activity will tell the sugar-shell
which class to start.

For example the most minimal Activity:


   from sugar.activity import activity

   class ReadActivity(activity.Activity):
        pass

To get a real, working activity, you will at least have to implement:
    __init__(), read_file() and write_file()

Aditionally, you will probably need a at least a Toolbar so you can have some
interesting buttons for the user, like for example 'exit activity'

See the methods of the Activity class below for more information on what you
will need for a real activity.

STABLE.
"""
# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2007-2009 One Laptop Per Child
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
import traceback
import gconf

import gtk
import gobject
import dbus
import dbus.service
import cjson

from sugar import util
from sugar.presence import presenceservice
from sugar.activity.activityservice import ActivityService
from sugar.activity.namingalert import NamingAlert
from sugar.graphics import style
from sugar.graphics.window import Window
from sugar.graphics.alert import Alert
from sugar.graphics.icon import Icon
from sugar.datastore import datastore
from sugar.session import XSMPClient
from sugar import wm

# support deprecated imports
from sugar.activity.widgets import ActivityToolbar, EditToolbar
from sugar.activity.widgets import ActivityToolbox


_ = lambda msg: gettext.dgettext('sugar-toolkit', msg)

SCOPE_PRIVATE = "private"
SCOPE_INVITE_ONLY = "invite"  # shouldn't be shown in UI, it's implicit
SCOPE_NEIGHBORHOOD = "public"

J_DBUS_SERVICE = 'org.laptop.Journal'
J_DBUS_PATH = '/org/laptop/Journal'
J_DBUS_INTERFACE = 'org.laptop.Journal'


class _ActivitySession(gobject.GObject):

    __gsignals__ = {
        'quit-requested': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'quit': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._xsmp_client = XSMPClient()
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
            gtk.main_quit()

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


class Activity(Window, gtk.Container):
    """This is the base Activity class that all other Activities derive from.
       This is where your activity starts.

    To get a working Activity:
        0. Derive your Activity from this class:
                class MyActivity(activity.Activity):
                    ...

        1. implement an __init__() method for your Activity class.

           Use your init method to create your own ActivityToolbar which will
           contain some standard buttons:
                toolbox = activity.ActivityToolbox(self)

           Add extra Toolbars to your toolbox.

           You should setup Activity sharing here too.

           Finaly, your Activity may need some resources which you can claim
           here too.

           The __init__() method is also used to make the distinction between
           being resumed from the Journal, or starting with a blank document.

        2. Implement read_file() and write_file()
           Most activities revolve around creating and storing Journal entries.
           For example, Write: You create a document, it is saved to the
           Journal and then later you resume working on the document.

           read_file() and write_file() will be called by sugar to tell your
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
           derive your own EditToolbar class from sugar.EditToolbar:
                class EditToolbar(activity.EditToolbar):
                    ...

           See EditToolbar for the methods you should implement in your class.

           Finaly, your Activity will very likely need some activity specific
           buttons and options you can create your own toolbars by deriving a
           class from gtk.Toolbar:
                class MySpecialToolbar(gtk.Toolbar):
                    ...

        4. Use your creativity. Make your Activity something special and share
           it with your friends!

    Read through the methods of the Activity class below, to learn more about
    how to make an Activity work.

    Hint: A good and simple Activity to learn from is the Read activity. To
    create your own activity, you may want to copy it and use it as a template.
    """

    __gtype_name__ = 'SugarActivity'

    __gsignals__ = {
        'shared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'joined': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
    }

    def __init__(self, handle, create_jobject=True):
        """Initialise the Activity

        handle -- sugar.activity.activityhandle.ActivityHandle
            instance providing the activity id and access to the
            presence service which *may* provide sharing for this
            application

        create_jobject -- boolean
            define if it should create a journal object if we are
            not resuming

        Side effects:

            Sets the gdk screen DPI setting (resolution) to the
            Sugar screen resolution.

            Connects our "destroy" message to our _destroy_cb
            method.

            Creates a base gtk.Window within this window.

            Creates an ActivityService (self._bus) servicing
            this application.

        Usage:
            If your Activity implements __init__(), it should call
            the base class __init()__ before doing Activity specific things.

        """
        Window.__init__(self)

        if os.environ.has_key('SUGAR_ACTIVITY_ROOT'):
            # If this activity runs inside Sugar, we want it to take all the
            # screen. Would be better if it was the shell to do this, but we
            # haven't found yet a good way to do it there. See #1263.
            self.connect('window-state-event', self.__window_state_event_cb)
            screen = gtk.gdk.screen_get_default()
            screen.connect('size-changed', self.__screen_size_changed_cb)
            self._adapt_window_to_screen()

        # process titles will only show 15 characters
        # but they get truncated anyway so if more characters
        # are supported in the future we will get a better view
        # of the processes
        proc_title = "%s <%s>" % (get_bundle_name(), handle.activity_id)
        util.set_proc_title(proc_title)

        self.connect('realize', self.__realize_cb)
        self.connect('delete-event', self.__delete_event_cb)

        self._active = False
        self._activity_id = handle.activity_id
        self._pservice = presenceservice.get_instance()
        self.shared_activity = None
        self._share_id = None
        self._join_id = None
        self._updating_jobject = False
        self._closing = False
        self._quit_requested = False
        self._deleting = False
        self._max_participants = 0
        self._invites_queue = []
        self._jobject = None
        self._read_file_called = False

        self._session = _get_session()
        self._session.register(self)
        self._session.connect('quit-requested',
                              self.__session_quit_requested_cb)
        self._session.connect('quit', self.__session_quit_cb)

        accel_group = gtk.AccelGroup()
        self.set_data('sugar-accel-group', accel_group)
        self.add_accel_group(accel_group)

        self._bus = ActivityService(self)
        self._owns_file = False

        share_scope = SCOPE_PRIVATE

        if handle.object_id:
            self._jobject = datastore.get(handle.object_id)
            self.set_title(self._jobject.metadata['title'])

            if self._jobject.metadata.has_key('share-scope'):
                share_scope = self._jobject.metadata['share-scope']

        # handle activity share/join
        mesh_instance = self._pservice.get_activity(self._activity_id,
                                                    warn_if_none=False)
        logging.debug("*** Act %s, mesh instance %r, scope %s",
                      self._activity_id, mesh_instance, share_scope)
        if mesh_instance is not None:
            # There's already an instance on the mesh, join it
            logging.debug("*** Act %s joining existing mesh instance %r",
                          self._activity_id, mesh_instance)
            self.shared_activity = mesh_instance
            self.shared_activity.connect('notify::private',
                                         self.__privacy_changed_cb)
            self._join_id = self.shared_activity.connect("joined",
                                                         self.__joined_cb)
            if not self.shared_activity.props.joined:
                self.shared_activity.join()
            else:
                self.__joined_cb(self.shared_activity, True, None)
        elif share_scope != SCOPE_PRIVATE:
            logging.debug('*** Act %s no existing mesh instance, but used to '
                'be shared, will share', self._activity_id)
            # no existing mesh instance, but activity used to be shared, so
            # restart the share
            if share_scope == SCOPE_INVITE_ONLY:
                self.share(private=True)
            elif share_scope == SCOPE_NEIGHBORHOOD:
                self.share(private=False)
            else:
                logging.debug('Unknown share scope %r', share_scope)

        if handle.object_id is None and create_jobject:
            logging.debug('Creating a jobject.')
            self._jobject = datastore.create()
            title = _('%s Activity') % get_bundle_name()
            self._jobject.metadata['title'] = title
            self.set_title(self._jobject.metadata['title'])
            self._jobject.metadata['title_set_by_user'] = '0'
            self._jobject.metadata['activity'] = self.get_bundle_id()
            self._jobject.metadata['activity_id'] = self.get_id()
            self._jobject.metadata['keep'] = '0'
            self._jobject.metadata['preview'] = ''
            self._jobject.metadata['share-scope'] = SCOPE_PRIVATE
            if self.shared_activity is not None:
                icon_color = self.shared_activity.props.color
            else:
                client = gconf.client_get_default()
                icon_color = client.get_string('/desktop/sugar/user/color')
            self._jobject.metadata['icon-color'] = icon_color

            self._jobject.file_path = ''
            # Cannot call datastore.write async for creates:
            # https://dev.laptop.org/ticket/3071
            datastore.write(self._jobject)

    def get_active(self):
        return self._active

    def set_active(self, active):
        if self._active != active:
            self._active = active
            if not self._active and self._jobject:
                self.save()

    active = gobject.property(
        type=bool, default=False, getter=get_active, setter=set_active)

    def get_max_participants(self):
        return self._max_participants

    def set_max_participants(self, participants):
        self._max_participants = participants

    max_participants = gobject.property(
            type=int, default=0, getter=get_max_participants,
            setter=set_max_participants)

    def get_id(self):
        """Returns the activity id of the current instance of your activity.

        The activity id is sort-of-like the unix process id (PID). However,
        unlike PIDs it is only different for each new instance (with
        create_jobject = True set) and stays the same everytime a user
        resumes an activity. This is also the identity of your Activity to
        other XOs for use when sharing.
        """
        return self._activity_id

    def get_bundle_id(self):
        """Returns the bundle_id from the activity.info file"""
        return os.environ['SUGAR_BUNDLE_ID']

    def set_canvas(self, canvas):
        """Sets the 'work area' of your activity with the canvas of your
        choice.

        One commonly used canvas is gtk.ScrolledWindow
        """
        Window.set_canvas(self, canvas)
        if not self._read_file_called:
            canvas.connect('map', self.__canvas_map_cb)

    def __screen_size_changed_cb(self, screen):
        self._adapt_window_to_screen()

    def __window_state_event_cb(self, window, event):
        self.move(0, 0)

    def _adapt_window_to_screen(self):
        screen = gtk.gdk.screen_get_default()
        self.set_geometry_hints(None,
                                screen.get_width(), screen.get_height(),
                                screen.get_width(), screen.get_height(),
                                screen.get_width(), screen.get_height(),
                                1, 1, 1, 1)

    def __session_quit_requested_cb(self, session):
        self._quit_requested = True

        if not self._prepare_close():
            session.will_quit(self, False)
        elif not self._updating_jobject:
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
        logging.debug('Error creating activity datastore object: %s', err)

    def get_activity_root(self):
        """ FIXME: Deprecated. This part of the API has been moved
        out of this class to the module itself

        Returns a path for saving Activity specific preferences, etc.

        Returns a path to the location in the filesystem where the activity can
        store activity related data that doesn't pertain to the current
        execution of the activity and thus cannot go into the DataStore.

        Currently, this will return something like
        ~/.sugar/default/MyActivityName/

        Activities should ONLY save settings, user preferences and other data
        which isn't specific to a journal item here. If (meta-)data is in
        anyway specific to a journal entry, it MUST be stored in the DataStore.
        """
        if os.environ.has_key('SUGAR_ACTIVITY_ROOT') and \
           os.environ['SUGAR_ACTIVITY_ROOT']:
            return os.environ['SUGAR_ACTIVITY_ROOT']
        else:
            return '/'

    def read_file(self, file_path):
        """
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
        """
        raise NotImplementedError

    def write_file(self, file_path):
        """
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
        """
        raise NotImplementedError

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
        logging.debug('Error saving activity object to datastore: %s', err)

    def _cleanup_jobject(self):
        if self._jobject:
            if self._owns_file and os.path.isfile(self._jobject.file_path):
                logging.debug('_cleanup_jobject: removing %r',
                    self._jobject.file_path)
                os.remove(self._jobject.file_path)
            self._owns_file = False
            self._jobject.destroy()
            self._jobject = None

    def get_preview(self):
        """Returns an image representing the state of the activity. Generally
        this is what the user is seeing in this moment.

        Activities can override this method, which should return a str with the
        binary content of a png image with a width of 300 and a height of 225
        pixels.
        """
        if self.canvas is None or not hasattr(self.canvas, 'get_snapshot'):
            return None
        pixmap = self.canvas.get_snapshot((-1, -1, 0, 0))

        width, height = pixmap.get_size()
        pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, 0, 8, width, height)
        pixbuf = pixbuf.get_from_drawable(pixmap, pixmap.get_colormap(),
                                          0, 0, 0, 0, width, height)
        pixbuf = pixbuf.scale_simple(style.zoom(300), style.zoom(225),
                                     gtk.gdk.INTERP_BILINEAR)

        preview_data = []

        def save_func(buf, data):
            data.append(buf)

        pixbuf.save_to_callback(save_func, 'png', user_data=preview_data)
        preview_data = ''.join(preview_data)

        return preview_data

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
        """Request that the activity is saved to the Journal.

        This method is called by the close() method below. In general,
        activities should not override this method. This method is part of the
        public API of an Acivity, and should behave in standard ways. Use your
        own implementation of write_file() to save your Activity specific data.
        """

        if self._jobject is None:
            logging.debug('Cannot save, no journal object.')
            return

        logging.debug('Activity.save: %r', self._jobject.object_id)

        if self._updating_jobject:
            logging.info('Activity.save: still processing a previous request.')
            return

        buddies_dict = self._get_buddies()
        if buddies_dict:
            self.metadata['buddies_id'] = cjson.encode(buddies_dict.keys())
            self.metadata['buddies'] = cjson.encode(self._get_buddies())

        preview = self.get_preview()
        if preview is not None:
            self.metadata['preview'] = dbus.ByteArray(preview)

        file_path = os.path.join(self.get_activity_root(), 'instance',
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
        """Request that the activity 'Keep in Journal' the current state
           of the activity.

        Activities should not override this method. Instead, like save() do any
        copy work that needs to be done in write_file()
        """
        logging.debug('Activity.copy: %r', self._jobject.object_id)
        self.save()
        self._jobject.object_id = None

    def __privacy_changed_cb(self, shared_activity, param_spec):
        if shared_activity.props.private:
            self._jobject.metadata['share-scope'] = SCOPE_INVITE_ONLY
        else:
            self._jobject.metadata['share-scope'] = SCOPE_NEIGHBORHOOD

    def __joined_cb(self, activity, success, err):
        """Callback when join has finished"""
        self.shared_activity.disconnect(self._join_id)
        self._join_id = None
        if not success:
            logging.debug('Failed to join activity: %s', err)
            return

        self.present()
        self.emit('joined')
        self.__privacy_changed_cb(self.shared_activity, None)

    def get_shared_activity(self):
        """Returns an instance of the shared Activity or None

        The shared activity is of type sugar.presence.activity.Activity
        """
        return self._shared_activity

    def get_shared(self):
        """Returns TRUE if the activity is shared on the mesh."""
        if not self.shared_activity:
            return False
        return self.shared_activity.props.joined

    def __share_cb(self, ps, success, activity, err):
        self._pservice.disconnect(self._share_id)
        self._share_id = None
        if not success:
            logging.debug('Share of activity %s failed: %s.',
                self._activity_id, err)
            return

        logging.debug('Share of activity %s successful, PS activity is %r.',
                      self._activity_id, activity)

        activity.props.name = self._jobject.metadata['title']

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
            buddy_key = self._invites_queue.pop()
            buddy = self._pservice.get_buddy(buddy_key)
            if buddy:
                self.shared_activity.invite(
                            buddy, '', self._invite_response_cb)
            else:
                logging.error('Cannot invite %s, no such buddy.', buddy_key)

    def invite(self, buddy_key):
        """Invite a buddy to join this Activity.

        Side Effects:
            Calls self.share(True) to privately share the activity if it wasn't
            shared before.
        """
        self._invites_queue.append(buddy_key)

        if (self.shared_activity is None
            or not self.shared_activity.props.joined):
            self.share(True)
        else:
            self._send_invites()

    def share(self, private=False):
        """Request that the activity be shared on the network.

        private -- bool: True to share by invitation only,
            False to advertise as shared to everyone.

        Once the activity is shared, its privacy can be changed by setting
        its 'private' property.
        """
        if self.shared_activity and self.shared_activity.props.joined:
            raise RuntimeError("Activity %s already shared." %
                               self._activity_id)
        verb = private and 'private' or 'public'
        logging.debug('Requesting %s share of activity %s.', verb,
            self._activity_id)
        self._share_id = self._pservice.connect("activity-shared",
                                                self.__share_cb)
        self._pservice.share_activity(self, private=private)

    def _show_keep_failed_dialog(self):
        alert = Alert()
        alert.props.title = _('Keep error')
        alert.props.msg = _('Keep error: all changes will be lost')

        cancel_icon = Icon(icon_name='dialog-cancel')
        alert.add_button(gtk.RESPONSE_CANCEL, _('Don\'t stop'), cancel_icon)

        stop_icon = Icon(icon_name='dialog-ok')
        alert.add_button(gtk.RESPONSE_OK, _('Stop anyway'), stop_icon)

        self.add_alert(alert)
        alert.connect('response', self._keep_failed_dialog_response_cb)

        self.present()

    def _keep_failed_dialog_response_cb(self, alert, response_id):
        self.remove_alert(alert)
        if response_id == gtk.RESPONSE_OK:
            self.close(skip_save=True)

    def can_close(self):
        """Activities should override this function if they want to perform
        extra checks before actually closing."""

        return True

    def _prepare_close(self, skip_save=False):
        if not skip_save:
            try:
                self.save()
            except:
                logging.info(traceback.format_exc())
                self._show_keep_failed_dialog()
                return False

        if self.shared_activity:
            self.shared_activity.leave()

        self._closing = True

        return True

    def _complete_close(self):
        self._cleanup_jobject()
        self.destroy()

        # Make the exported object inaccessible
        dbus.service.Object.remove_from_connection(self._bus)

        self._session.unregister(self)

    def close(self, skip_save=False):
        """Request that the activity be stopped and saved to the Journal

        Activities should not override this method, but should implement
        write_file() to do any state saving instead. If the application wants
        to control wether it can close, it should override can_close().
        """
        if not self.can_close():
            return

        if skip_save or self.metadata.get('title_set_by_user', '0') == '1':
            if not self._closing:
                if not self._prepare_close(skip_save):
                    return

            if not self._updating_jobject:
                self._complete_close()
        else:
            title_alert = NamingAlert(self, get_bundle_path())
            title_alert.set_transient_for(self.get_toplevel())
            title_alert.show()
            self.present()

    def __realize_cb(self, window):
        wm.set_bundle_id(window.window, self.get_bundle_id())
        wm.set_activity_id(window.window, str(self._activity_id))

    def __delete_event_cb(self, widget, event):
        self.close()
        return True

    def get_metadata(self):
        """Returns the jobject metadata or None if there is no jobject.

        Activities can set metadata in write_file() using:
            self.metadata['MyKey'] = "Something"

        and retrieve metadata in read_file() using:
            self.metadata.get('MyKey', 'aDefaultValue')

        Note: Make sure your activity works properly if one or more of the
        metadata items is missing. Never assume they will all be present.
        """
        if self._jobject:
            return self._jobject.metadata
        else:
            return None

    metadata = property(get_metadata, None)

    def handle_view_source(self):
        raise NotImplementedError

    def get_document_path(self, async_cb, async_err_cb):
        async_err_cb(NotImplementedError())

    # DEPRECATED
    _shared_activity = property(lambda self: self.shared_activity, None)


_session = None


def _get_session():
    global _session

    if _session is None:
        _session = _ActivitySession()

    return _session


def get_bundle_name():
    """Return the bundle name for the current process' bundle"""
    return os.environ['SUGAR_BUNDLE_NAME']


def get_bundle_path():
    """Return the bundle path for the current process' bundle"""
    return os.environ['SUGAR_BUNDLE_PATH']


def get_activity_root():
    """Returns a path for saving Activity specific preferences, etc."""
    if os.environ.has_key('SUGAR_ACTIVITY_ROOT') and \
            os.environ['SUGAR_ACTIVITY_ROOT']:
        return os.environ['SUGAR_ACTIVITY_ROOT']
    else:
        raise RuntimeError("No SUGAR_ACTIVITY_ROOT set.")


def show_object_in_journal(object_id):
    bus = dbus.SessionBus()
    obj = bus.get_object(J_DBUS_SERVICE, J_DBUS_PATH)
    journal = dbus.Interface(obj, J_DBUS_INTERFACE)
    journal.ShowObject(object_id)

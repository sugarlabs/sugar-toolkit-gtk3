# Copyright (C) 2007, Red Hat, Inc.
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

"""UI interface to an activity in the presence service

STABLE.
"""

import logging
from functools import partial

import dbus
import gobject
import telepathy
from telepathy.client import Channel
from telepathy.interfaces import CHANNEL, \
                                 CHANNEL_TYPE_TUBES, \
                                 CHANNEL_TYPE_TEXT, \
                                 CONNECTION
from telepathy.constants import HANDLE_TYPE_ROOM

CONN_INTERFACE_ACTIVITY_PROPERTIES = 'org.laptop.Telepathy.ActivityProperties'
CONN_INTERFACE_BUDDY_INFO = 'org.laptop.Telepathy.BuddyInfo'

_logger = logging.getLogger('sugar.presence.activity')


class Activity(gobject.GObject):
    """UI interface for an Activity in the presence service

    Activities in the presence service represent your and other user's
    shared activities.

    Properties:
        id
        color
        name
        type
        joined
    """
    __gsignals__ = {
        'buddy-joined': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
            ([gobject.TYPE_PYOBJECT])),
        'buddy-left': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
            ([gobject.TYPE_PYOBJECT])),
        'new-channel': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
            ([gobject.TYPE_PYOBJECT])),
        'joined': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
            ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
    }

    __gproperties__ = {
        'id': (str, None, None, None, gobject.PARAM_READABLE),
        'name': (str, None, None, None, gobject.PARAM_READWRITE),
        'tags': (str, None, None, None, gobject.PARAM_READWRITE),
        'color': (str, None, None, None, gobject.PARAM_READWRITE),
        'type': (str, None, None, None, gobject.PARAM_READABLE),
        'private': (bool, None, None, True, gobject.PARAM_READWRITE),
        'joined': (bool, None, None, False, gobject.PARAM_READABLE),
    }

    def __init__(self, connection, room_handle=None, properties=None):
        if room_handle is None and properties is None:
            raise ValueError('Need to pass one of room_handle or properties')

        if properties is None:
            properties = {}

        gobject.GObject.__init__(self)

        self.telepathy_conn = connection
        self.telepathy_text_chan = None
        self.telepathy_tubes_chan = None

        self._room_handle = room_handle
        self._id = properties.get('id', None)
        self._color = properties.get('color', None)
        self._name = properties.get('name', None)
        self._type = properties.get('type', None)
        self._tags = properties.get('tags', None)
        self._private = properties.get('private', True)
        self._joined = properties.get('joined', False)

        self._get_properties_call = None
        if not self._room_handle is None:
            self._start_tracking_properties()

    def _start_tracking_properties(self):
        bus = dbus.SessionBus()
        self._get_properties_call = bus.call_async(
                self.telepathy_conn.requested_bus_name,
                self.telepathy_conn.object_path,
                CONN_INTERFACE_ACTIVITY_PROPERTIES,
                'GetProperties',
                'u',
                (self._room_handle,),
                reply_handler=self._got_properties_cb,
                error_handler=self._error_handler_cb,
                utf8_strings=True)

        # As only one Activity instance is needed per activity process,
        # we can afford listening to ActivityPropertiesChanged like this.
        self.telepathy_conn.connect_to_signal(
                'ActivityPropertiesChanged',
                self.__activity_properties_changed_cb,
                dbus_interface=CONN_INTERFACE_ACTIVITY_PROPERTIES)

    def __activity_properties_changed_cb(self, room_handle, properties):
        _logger.debug('%r: Activity properties changed to %r', self, properties)
        self._update_properties(properties)

    def _got_properties_cb(self, properties):
        _logger.debug('_got_properties_cb %r', properties)
        self._get_properties_call = None
        self._update_properties(properties)

    def _error_handler_cb(self, error):
        _logger.debug('_error_handler_cb %r', error)

    def _update_properties(self, new_props):
        val = new_props.get('name', self._name)
        if isinstance(val, str) and val != self._name:
            self._name = val
            self.notify('name')
        val = new_props.get('tags', self._tags)
        if isinstance(val, str) and val != self._tags:
            self._tags = val
            self.notify('tags')
        val = new_props.get('color', self._color)
        if isinstance(val, str) and val != self._color:
            self._color = val
            self.notify('color')
        val = bool(new_props.get('private', self._private))
        if val != self._private:
            self._private = val
            self.notify('private')
        val = new_props.get('id', self._id)
        if isinstance(val, str) and self._id is None:
            self._id = val
            self.notify('id')
        val = new_props.get('type', self._type)
        if isinstance(val, str) and self._type is None:
            self._type = val
            self.notify('type')

    def object_path(self):
        """Get our dbus object path"""
        return self._object_path

    def do_get_property(self, pspec):
        """Retrieve a particular property from our property dictionary"""

        if pspec.name == "joined":
            return self._joined

        if self._get_properties_call is not None:
            _logger.debug('%r: Blocking on GetProperties() because someone '
                          'wants property %s', self, pspec.name)
            self._get_properties_call.block()

        if pspec.name == "id":
            return self._id
        elif pspec.name == "name":
            return self._name
        elif pspec.name == "color":
            return self._color
        elif pspec.name == "type":
            return self._type
        elif pspec.name == "tags":
            return self._tags
        elif pspec.name == "private":
            return self._private

    def do_set_property(self, pspec, val):
        """Set a particular property in our property dictionary"""
        # FIXME: need an asynchronous API to set these properties,
        # particularly 'private'

        if pspec.name == "name":
            self._name = val
        elif pspec.name == "color":
            self._color = val
        elif pspec.name == "tags":
            self._tags = val
        elif pspec.name == "private":
            self._private = val
        else:
            raise ValueError('Unknown property "%s"', pspec.name)

        self._publish_properties()

    def set_private(self, val, reply_handler, error_handler):
        _logger.debug('set_private %r', val)
        self._activity.SetProperties({'private': bool(val)},
                                     reply_handler=reply_handler,
                                     error_handler=error_handler)

    def _emit_buddy_joined_signal(self, object_path):
        """Generate buddy-joined GObject signal with presence Buddy object"""
        self.emit('buddy-joined', self._ps_new_object(object_path))
        return False

    def _buddy_handle_joined_cb(self, object_path, handle):
        _logger.debug('%r: buddy %s joined with handle %u', self, object_path,
                      handle)
        gobject.idle_add(self._emit_buddy_joined_signal, object_path)
        self._handle_to_buddy_path[handle] = object_path
        self._buddy_path_to_handle[object_path] = handle

    def _emit_buddy_left_signal(self, object_path):
        """Generate buddy-left GObject signal with presence Buddy object

        XXX note use of _ps_new_object instead of _ps_del_object here
        """
        self.emit('buddy-left', self._ps_new_object(object_path))
        return False

    def _buddy_left_cb(self, object_path):
        _logger.debug('%r: buddy %s left', self, object_path)
        gobject.idle_add(self._emit_buddy_left_signal, object_path)
        handle = self._buddy_path_to_handle.pop(object_path, None)
        if handle:
            self._handle_to_buddy_path.pop(handle, None)

    def _emit_new_channel_signal(self, object_path):
        """Generate new-channel GObject signal with channel object path

        New telepathy-python communications channel has been opened
        """
        self.emit('new-channel', object_path)
        return False

    def _new_channel_cb(self, object_path):
        _logger.debug('%r: new channel created at %s', self, object_path)
        gobject.idle_add(self._emit_new_channel_signal, object_path)

    def get_joined_buddies(self):
        """Retrieve the set of Buddy objects attached to this activity

        returns list of presence Buddy objects that we can successfully
        create from the buddy object paths that PS has for this activity.
        """
        logging.info('KILL_PS return joined buddies')
        return []

    def get_buddy_by_handle(self, handle):
        """Retrieve the Buddy object given a telepathy handle.

        buddy object paths are cached in self._handle_to_buddy_path,
        so we can get the buddy without calling PS.
        """
        object_path = self._handle_to_buddy_path.get(handle, None)
        if object_path:
            buddy = self._ps_new_object(object_path)
            return buddy
        return None

    def invite(self, buddy, message, response_cb):
        """Invite the given buddy to join this activity.

        The callback will be called with one parameter: None on success,
        or an exception on failure.
        """
        op = buddy.object_path()
        _logger.debug('%r: inviting %s', self, op)
        self._activity.Invite(op, message,
                              reply_handler=lambda: response_cb(None),
                              error_handler=response_cb)

    # Joining and sharing (FIXME: sharing is actually done elsewhere)

    def set_up_tubes(self, reply_handler, error_handler):

        if self._room_handle is None:
            raise ValueError("Don't have a handle for the room yet")

        chans = []

        def tubes_ready():
            if self.telepathy_text_chan is None or \
               self.telepathy_tubes_chan is None:
                return

            _logger.debug('%r: finished setting up tubes', self)
            reply_handler()

        def tubes_channel_ready_cb(channel):
            _logger.debug('%r: Tubes channel %r is ready', self, channel)
            self.telepathy_tubes_chan = channel
            tubes_ready()

        def text_channel_ready_cb(channel):
            _logger.debug('%r: Text channel %r is ready', self, channel)
            self.telepathy_text_chan = channel
            tubes_ready()

        def create_text_channel_cb(channel_path):
            Channel(self.telepathy_conn.requested_bus_name, channel_path,
                    ready_handler=text_channel_ready_cb)

        def create_tubes_channel_cb(channel_path):
            Channel(self.telepathy_conn.requested_bus_name, channel_path,
                    ready_handler=tubes_channel_ready_cb)

        def error_handler_cb(error):
            raise RuntimeError(error)

        self.telepathy_conn.RequestChannel(CHANNEL_TYPE_TEXT,
            HANDLE_TYPE_ROOM, self._room_handle, True,
            reply_handler=create_text_channel_cb,
            error_handler=error_handler_cb,
            dbus_interface=CONNECTION)

        self.telepathy_conn.RequestChannel(CHANNEL_TYPE_TUBES,
            HANDLE_TYPE_ROOM, self._room_handle, True,
            reply_handler=create_tubes_channel_cb,
            error_handler=error_handler_cb,
            dbus_interface=CONNECTION)

    def _join_cb(self):
        _logger.debug('%r: Join finished', self)
        self._joined = True
        self.emit("joined", True, None)

    def _join_error_cb(self, err):
        _logger.debug('%r: Join failed because: %s', self, err)
        self.emit("joined", False, str(err))

    def join(self):
        """Join this activity.

        Emits 'joined' and otherwise does nothing if we're already joined.
        """
        if self._joined:
            self.emit("joined", True, None)
            return

        _logger.debug('%r: joining', self)

        self.set_up_tubes(reply_handler=self._join_cb,
                          error_handler=self._join_error_cb)

    def share(self, share_activity_cb, share_activity_error_cb):
        if not self._room_handle is None:
            raise ValueError('Already have a room handle')

        """ TODO: Check we don't need this
        # We shouldn't have to do this, but Gabble sometimes finds the IRC
        # transport and goes "that has chatrooms, that'll do nicely". Work
        # around it til Gabble gets better at finding the MUC service.
        return '%s@%s' % (activity_id,
                          self._account['fallback-conference-server'])
        """

        self.telepathy_conn.RequestHandles(
            HANDLE_TYPE_ROOM,
            [self._id],
            reply_handler=partial(self.__got_handles_cb, share_activity_cb, share_activity_error_cb),
            error_handler=partial(self.__share_error_cb, share_activity_error_cb),
            dbus_interface=CONNECTION)

    def __got_handles_cb(self, share_activity_cb, share_activity_error_cb, handles):
        logging.debug('__got_handles_cb %r', handles)
        self._room_handle = handles[0]
        self._joined = True

        self.set_up_tubes(
                partial(self.__tubes_set_up_cb, share_activity_cb, share_activity_error_cb),
                share_activity_error_cb)

    def __tubes_set_up_cb(self, share_activity_cb, share_activity_error_cb):
        self.telepathy_conn.AddActivity(
            self._id,
            self._room_handle,
            reply_handler=partial(self.__added_activity_cb, share_activity_cb),
            error_handler=partial(self.__share_error_cb, share_activity_error_cb),
            dbus_interface=CONN_INTERFACE_BUDDY_INFO)

    def __added_activity_cb(self, share_activity_cb):
        self._publish_properties()
        self._start_tracking_properties()
        share_activity_cb(self)

    def _publish_properties(self):
        properties = {}

        if self._color is not None:
            properties['color'] = self._color
        if self._name is not None:
            properties['name'] = self._name
        if self._type is not None:
            properties['type'] = self._type
        if self._tags is not None:
            properties['tags'] = self._tags
        properties['private'] = self._private

        logging.debug('_publish_properties calling SetProperties')
        self.telepathy_conn.SetProperties(
                self._room_handle,
                properties,
                dbus_interface=CONN_INTERFACE_ACTIVITY_PROPERTIES)

    def __share_error_cb(self, share_activity_error_cb, error):
        logging.debug('%r: Share failed because: %s', self, error)
        share_activity_error_cb(self, error)

    # GetChannels() wrapper

    def get_channels(self):
        """Retrieve communications channel descriptions for the activity

        Returns a tuple containing:
            - the D-Bus well-known service name of the connection
              (FIXME: this is redundant; in Telepathy it can be derived
              from that of the connection)
            - the D-Bus object path of the connection
            - a list of D-Bus object paths representing the channels
              associated with this activity
        """
        (bus_name, connection, channels) = self._activity.GetChannels()
        _logger.debug('%r: bus name is %s, connection is %s, channels are %r',
                      self, bus_name, connection, channels)
        return bus_name, connection, channels

    # Leaving

    def _leave_cb(self):
        """Callback for async action of leaving shared activity."""
        self.emit("joined", False, "left activity")

    def _leave_error_cb(self, err):
        """Callback for error in async leaving of shared activity."""
        _logger.debug('Failed to leave activity: %s', err)

    def leave(self):
        """Leave this shared activity"""
        _logger.debug('%r: leaving', self)
        self._joined = False
        self._activity.Leave(reply_handler=self._leave_cb,
                             error_handler=self._leave_error_cb)

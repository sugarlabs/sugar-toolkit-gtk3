# Copyright (C) 2007, Red Hat, Inc.
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

"""UI interface to an activity in the presence service

STABLE.
"""

import six
import logging
from functools import partial

import gi
gi.require_version('TelepathyGLib', '0.12')
import dbus
from dbus import PROPERTIES_IFACE
from gi.repository import GObject
from gi.repository import TelepathyGLib

from sugar3.presence.buddy import Buddy

CHANNEL = TelepathyGLib.IFACE_CHANNEL
CHANNEL_INTERFACE_GROUP = TelepathyGLib.IFACE_CHANNEL_INTERFACE_GROUP
CONN_INTERFACE_ROOM_CONFIG = \
    TelepathyGLib.IFACE_CHANNEL_INTERFACE_ROOM_CONFIG
CHANNEL_TYPE_TUBES = TelepathyGLib.IFACE_CHANNEL_TYPE_TUBES
CHANNEL_TYPE_TEXT = TelepathyGLib.IFACE_CHANNEL_TYPE_TEXT
CONNECTION = TelepathyGLib.IFACE_CONNECTION
PROPERTIES_INTERFACE = TelepathyGLib.IFACE_PROPERTIES_INTERFACE

CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES = \
    TelepathyGLib.ChannelGroupFlags.CHANNEL_SPECIFIC_HANDLES
HANDLE_TYPE_CONTACT = TelepathyGLib.HandleType.CONTACT
HANDLE_TYPE_ROOM = TelepathyGLib.HandleType.ROOM
PROPERTY_FLAG_WRITE = TelepathyGLib.PropertyFlags.WRITE

CONN_INTERFACE_ACTIVITY_PROPERTIES = 'org.laptop.Telepathy.ActivityProperties'
CONN_INTERFACE_BUDDY_INFO = 'org.laptop.Telepathy.BuddyInfo'

_logger = logging.getLogger('sugar3.presence.activity')


if not hasattr(GObject.ParamFlags, 'READWRITE'):
    GObject.ParamFlags.READWRITE = GObject.ParamFlags.WRITABLE | \
        GObject.ParamFlags.READABLE


class Activity(GObject.GObject):
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
        'buddy-joined': (GObject.SignalFlags.RUN_FIRST, None,
                         ([GObject.TYPE_PYOBJECT])),
        'buddy-left': (GObject.SignalFlags.RUN_FIRST, None,
                       ([GObject.TYPE_PYOBJECT])),
        'new-channel': (GObject.SignalFlags.RUN_FIRST, None,
                        ([GObject.TYPE_PYOBJECT])),
        'joined': (GObject.SignalFlags.RUN_FIRST, None,
                   ([GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT])),
    }

    __gproperties__ = {
        'id': (str, None, None, None, GObject.ParamFlags.READABLE),
        'name': (str, None, None, None, GObject.ParamFlags.READWRITE),
        'tags': (str, None, None, None, GObject.ParamFlags.READWRITE),
        'color': (str, None, None, None, GObject.ParamFlags.READWRITE),
        'type': (str, None, None, None, GObject.ParamFlags.READABLE),
        'private': (bool, None, None, True, GObject.ParamFlags.READWRITE),
        'joined': (bool, None, None, False, GObject.ParamFlags.READABLE),
    }

    def __init__(self, account_path, connection, room_handle=None,
                 properties=None):
        if room_handle is None and properties is None:
            raise ValueError('Need to pass one of room_handle or properties')

        if properties is None:
            properties = {}

        GObject.GObject.__init__(self)

        self._account_path = account_path
        self.telepathy_conn = connection
        self.telepathy_text_chan = None
        self.telepathy_tubes_chan = None

        self.room_handle = room_handle
        self._join_command = None
        self._share_command = None
        self._id = properties.get('id', None)
        self._color = properties.get('color', None)
        self._name = properties.get('name', None)
        self._type = properties.get('type', None)
        self._tags = properties.get('tags', None)
        self._private = properties.get('private', True)
        self._joined = properties.get('joined', False)
        self._channel_self_handle = None
        self._text_channel_group_flags = 0
        self._buddies = {}
        self._joined_buddies = {}

        self._get_properties_call = None
        if self.room_handle is not None:
            self._start_tracking_properties()

    def _start_tracking_properties(self):
        bus = dbus.SessionBus()
        if six.PY2:
            self._get_properties_call = bus.call_async(
                self.telepathy_conn.requested_bus_name,
                self.telepathy_conn.object_path,
                CONN_INTERFACE_ACTIVITY_PROPERTIES,
                'GetProperties',
                'u',
                (self.room_handle,),
                reply_handler=self.__got_properties_cb,
                error_handler=self.__error_handler_cb,
                utf8_strings=True)
        else:
            self._get_properties_call = bus.call_async(
                self.telepathy_conn.requested_bus_name,
                self.telepathy_conn.object_path,
                CONN_INTERFACE_ACTIVITY_PROPERTIES,
                'GetProperties',
                'u',
                (self.room_handle,),
                reply_handler=self.__got_properties_cb,
                error_handler=self.__error_handler_cb)

        # As only one Activity instance is needed per activity process,
        # we can afford listening to ActivityPropertiesChanged like this.
        self.telepathy_conn.connect_to_signal(
            'ActivityPropertiesChanged',
            self.__activity_properties_changed_cb,
            dbus_interface=CONN_INTERFACE_ACTIVITY_PROPERTIES)

    def __activity_properties_changed_cb(self, room_handle, properties):
        _logger.debug('%r: Activity properties changed to %r' % (self,
                                                                 properties))
        self._update_properties(properties)

    def __got_properties_cb(self, properties):
        _logger.debug('__got_properties_cb %r' % properties)
        self._get_properties_call = None
        self._update_properties(properties)

    def __error_handler_cb(self, error):
        _logger.debug('__error_handler_cb %r' % error)

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

        if pspec.name == 'joined':
            return self._joined

        if self._get_properties_call is not None:
            _logger.debug('%r: Blocking on GetProperties() because someone '
                          'wants property %s' % (self, pspec.name))
            self._get_properties_call.block()

        if pspec.name == 'id':
            return self._id
        elif pspec.name == 'name':
            return self._name
        elif pspec.name == 'color':
            return self._color
        elif pspec.name == 'type':
            return self._type
        elif pspec.name == 'tags':
            return self._tags
        elif pspec.name == 'private':
            return self._private

    def do_set_property(self, pspec, val):
        """Set a particular property in our property dictionary"""
        # FIXME: need an asynchronous API to set these properties,
        # particularly 'private'

        if pspec.name == 'name':
            self._name = val
        elif pspec.name == 'color':
            self._color = val
        elif pspec.name == 'tags':
            self._tags = val
        elif pspec.name == 'private':
            self._private = val
        else:
            raise ValueError('Unknown property %r' % pspec.name)

        self._publish_properties()

    def set_private(self, val, reply_handler, error_handler):
        _logger.debug('set_private %r' % val)
        self._activity.SetProperties({'private': bool(val)},
                                     reply_handler=reply_handler,
                                     error_handler=error_handler)

    def get_joined_buddies(self):
        """Retrieve the set of Buddy objects attached to this activity

        returns list of presence Buddy objects that we can successfully
        create from the buddy object paths that PS has for this activity.
        """
        return list(self._joined_buddies.values())

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
        if not self._joined:
            raise RuntimeError('Cannot invite a buddy to an activity that is'
                               'not shared.')
        self.telepathy_text_chan[CHANNEL].AddMembers(
            [buddy.contact_handle], message,
            dbus_interface=CHANNEL_INTERFACE_GROUP,
            reply_handler=partial(
                self.__invite_cb, response_cb),
            error_handler=partial(self.__invite_cb, response_cb))

    def __invite_cb(self, response_cb, error=None):
        response_cb(error)

    def set_up_tubes(self, reply_handler, error_handler):
        raise NotImplementedError()

    def __joined_cb(self, join_command, error):
        _logger.debug('%r: Join finished %r' % (self, error))
        if error is not None:
            self.emit('joined', error is None, str(error))
        self.telepathy_text_chan = join_command.text_channel
        self.telepathy_tubes_chan = join_command.tubes_channel
        self._channel_self_handle = join_command.channel_self_handle
        self._text_channel_group_flags = join_command.text_channel_group_flags
        self._start_tracking_buddies()
        self._start_tracking_channel()

    def _start_tracking_buddies(self):
        group = self.telepathy_text_chan[CHANNEL_INTERFACE_GROUP]

        group.GetAllMembers(reply_handler=self.__get_all_members_cb,
                            error_handler=self.__error_handler_cb)

        group.connect_to_signal('MembersChanged',
                                self.__text_channel_members_changed_cb)

    def _start_tracking_channel(self):
        channel = self.telepathy_text_chan[CHANNEL]
        channel.connect_to_signal('Closed', self.__text_channel_closed_cb)

    def __get_all_members_cb(self, members, local_pending, remote_pending):
        _logger.debug(
            '__get_all_members_cb %r %r' %
            (members, self._text_channel_group_flags))
        if self._channel_self_handle in members:
            members.remove(self._channel_self_handle)

        if not members:
            return

        self._resolve_handles(members, reply_cb=self._add_initial_buddies)

    def _resolve_handles(self, input_handles, reply_cb):
        def get_handle_owners_cb(handles):
            self.telepathy_conn.InspectHandles(
                HANDLE_TYPE_CONTACT, handles,
                reply_handler=reply_cb,
                error_handler=self.__error_handler_cb,
                dbus_interface=CONNECTION)

        if self._text_channel_group_flags & \
                CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES:

            group = self.telepathy_text_chan[CHANNEL_INTERFACE_GROUP]
            group.GetHandleOwners(input_handles,
                                  reply_handler=get_handle_owners_cb,
                                  error_handler=self.__error_handler_cb)
        else:
            get_handle_owners_cb(input_handles)

    def _add_initial_buddies(self, contact_ids):
        _logger.debug('__add_initial_buddies %r' % contact_ids)
        for contact_id in contact_ids:
            self._buddies[contact_id] = self._get_buddy(contact_id)
            self._joined_buddies[contact_id] = self._get_buddy(contact_id)
        # Once we have the initial members, we can finish the join process
        self._joined = True
        self.emit('joined', True, None)

    def __text_channel_members_changed_cb(self, message, added, removed,
                                          local_pending, remote_pending,
                                          actor, reason):
        _logger.debug('__text_channel_members_changed_cb %r' %
                      [added, message, added, removed, local_pending,
                       remote_pending, actor, reason])
        if self._channel_self_handle in added:
            added.remove(self._channel_self_handle)
        if added:
            self._resolve_handles(added, reply_cb=self._add_buddies)

        if self._channel_self_handle in removed:
            removed.remove(self._channel_self_handle)
        if removed:
            self._resolve_handles(removed, reply_cb=self._remove_buddies)

    def _add_buddies(self, contact_ids):
        for contact_id in contact_ids:
            if contact_id not in self._buddies:
                buddy = self._get_buddy(contact_id)
                self.emit('buddy-joined', buddy)
                self._buddies[contact_id] = buddy
            if contact_id not in self._joined_buddies:
                self._joined_buddies[contact_id] = buddy

    def _remove_buddies(self, contact_ids):
        for contact_id in contact_ids:
            if contact_id in self._buddies:
                buddy = self._get_buddy(contact_id)
                self.emit('buddy-left', buddy)
                del self._buddies[contact_id]

    def _get_buddy(self, contact_id):
        if contact_id in self._buddies:
            return self._buddies[contact_id]
        else:
            return Buddy(self._account_path, contact_id)

    def join(self):
        """Join this activity.

        Emits 'joined' and otherwise does nothing if we're already joined.
        """
        if self._join_command is not None:
            return

        if self._joined:
            self.emit('joined', True, None)
            return

        _logger.debug('%r: joining' % self)

        self._join_command = _JoinCommand(self.telepathy_conn,
                                          self.room_handle)
        self._join_command.connect('finished', self.__joined_cb)
        self._join_command.run()

    def share(self, share_activity_cb, share_activity_error_cb):
        if self.room_handle is not None:
            raise ValueError('Already have a room handle')

        self._share_command = _ShareCommand(self.telepathy_conn, self._id)
        self._share_command.connect('finished',
                                    partial(self.__shared_cb,
                                            share_activity_cb,
                                            share_activity_error_cb))
        self._share_command.run()

    def __shared_cb(self, share_activity_cb, share_activity_error_cb,
                    share_command, error):
        _logger.debug('%r: Share finished %r' % (self, error))
        if error is None:
            self._joined = True
            self.room_handle = share_command.room_handle
            self.telepathy_text_chan = share_command.text_channel
            self.telepathy_tubes_chan = share_command.tubes_channel
            self._channel_self_handle = share_command.channel_self_handle
            self._text_channel_group_flags = \
                share_command.text_channel_group_flags
            self._publish_properties()
            self._start_tracking_properties()
            self._start_tracking_buddies()
            self._start_tracking_channel()
            share_activity_cb(self)
        else:
            share_activity_error_cb(self, error)

    def _publish_properties(self):
        properties = {}

        if self._color is not None:
            properties['color'] = str(self._color)
        if self._name is not None:
            properties['name'] = str(self._name)
        if self._type is not None:
            properties['type'] = self._type
        if self._tags is not None:
            properties['tags'] = self._tags
        properties['private'] = self._private

        self.telepathy_conn.SetProperties(
            self.room_handle,
            properties,
            dbus_interface=CONN_INTERFACE_ACTIVITY_PROPERTIES)

    def __share_error_cb(self, share_activity_error_cb, error):
        logging.debug('%r: Share failed because: %s' % (self, error))
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
        bus_name = self.telepathy_conn.requested_bus_name
        connection_path = self.telepathy_conn.object_path
        channels = [self.telepathy_text_chan.object_path,
                    self.telepathy_tubes_chan.object_path]

        _logger.debug('%r: bus name is %s, connection is %s, channels are %r' %
                      (self, bus_name, connection_path, channels))
        return bus_name, connection_path, channels

    # Leaving
    def __text_channel_closed_cb(self):
        self._joined = False
        self.emit('joined', False, 'left activity')

    def leave(self):
        """Leave this shared activity"""
        _logger.debug('%r: leaving' % self)
        self.telepathy_text_chan[CHANNEL].Close()


class _BaseCommand(GObject.GObject):
    __gsignals__ = {
        'finished': (GObject.SignalFlags.RUN_FIRST, None,
                     ([object])),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self.text_channel = None
        self.text_channel_group_flags = None
        self.tubes_channel = None
        self.room_handle = None
        self.channel_self_handle = None

    def run(self):
        raise NotImplementedError()


class _ShareCommand(_BaseCommand):
    def __init__(self, connection, activity_id):
        _BaseCommand.__init__(self)

        self._connection = connection
        self._activity_id = activity_id
        self._finished = False
        self._join_command = None

    def run(self):
        self._connection.RequestHandles(
            HANDLE_TYPE_ROOM,
            [self._activity_id],
            reply_handler=self.__got_handles_cb,
            error_handler=self.__error_handler_cb,
            dbus_interface=CONNECTION)

    def __got_handles_cb(self, handles):
        logging.debug('__got_handles_cb %r' % handles)
        self.room_handle = handles[0]

        self._join_command = _JoinCommand(self._connection, self.room_handle)
        self._join_command.connect('finished', self.__joined_cb)
        self._join_command.run()

    def __joined_cb(self, join_command, error):
        _logger.debug('%r: Join finished %r' % (self, error))
        if error is not None:
            self._finished = True
            self.emit('finished', error)
            return

        self.text_channel = join_command.text_channel
        self.text_channel_group_flags = join_command.text_channel_group_flags
        self.tubes_channel = join_command.tubes_channel
        self.channel_self_handle = join_command.channel_self_handle

        self._connection.AddActivity(
            self._activity_id,
            self.room_handle,
            reply_handler=self.__added_activity_cb,
            error_handler=self.__error_handler_cb,
            dbus_interface=CONN_INTERFACE_BUDDY_INFO)

    def __added_activity_cb(self):
        self._finished = True
        self.emit('finished', None)

    def __error_handler_cb(self, error):
        self._finished = True
        self.emit('finished', error)


class _JoinCommand(_BaseCommand):
    def __init__(self, connection, room_handle):
        _BaseCommand.__init__(self)

        self._connection = connection
        self._finished = False
        self.room_handle = room_handle
        self._global_self_handle = None
        self._tubes_supported = True

    def run(self):
        if self._finished:
            raise RuntimeError('This command has already finished')

        self._connection.Get(CONNECTION, 'SelfHandle',
                             reply_handler=self.__get_self_handle_cb,
                             error_handler=self.__error_handler_cb,
                             dbus_interface=PROPERTIES_IFACE)

    def __get_self_handle_cb(self, handle):
        self._global_self_handle = handle

        self._text_ready = False
        self._connection.RequestChannel(
            CHANNEL_TYPE_TEXT,
            HANDLE_TYPE_ROOM,
            self.room_handle, True,
            reply_handler=self.__create_text_channel_cb,
            error_handler=self.__error_handler_cb,
            dbus_interface=CONNECTION)

        self._tubes_ready = False
        self._connection.RequestChannel(
            CHANNEL_TYPE_TUBES,
            HANDLE_TYPE_ROOM,
            self.room_handle,
            True,
            reply_handler=self.__create_tubes_channel_cb,
            error_handler=self.__tubes_error_handler_cb,
            dbus_interface=CONNECTION)

    def __create_text_channel_cb(self, channel_path):
        self.text_channel = {}
        self.text_proxy = dbus.Bus().get_object(
            self._connection.requested_bus_name, channel_path)
        self.text_channel[PROPERTIES_IFACE] = dbus.Interface(
            self.text_proxy, PROPERTIES_IFACE)
        self.text_channel[CHANNEL_TYPE_TEXT] = \
            dbus.Interface(self.text_proxy, CHANNEL_TYPE_TEXT)
        self.text_channel[CHANNEL] = dbus.Interface(self.text_proxy, CHANNEL)
        self.text_channel[CHANNEL].GetInterfaces(
            reply_handler=self.__text_get_interfaces_reply_cb,
            error_handler=self.__error_handler_cb)

    def __text_get_interfaces_reply_cb(self, interfaces):
        for interface in interfaces:
            self.text_channel[interface] = dbus.Interface(
                self.text_proxy, interface)
        _logger.debug('%r: Text channel is ready' % (self))
        self._text_ready = True
        self._ready()

    def __create_tubes_channel_cb(self, channel_path):
        self.tubes_channel = {}
        self.tubes_proxy = dbus.Bus().get_object(
            self._connection.requested_bus_name, channel_path)
        self.tubes_channel[PROPERTIES_IFACE] = dbus.Interface(
            self.tubes_proxy, PROPERTIES_IFACE)
        self.tubes_channel[CHANNEL_TYPE_TUBES] = \
            dbus.Interface(self.tubes_proxy, CHANNEL_TYPE_TUBES)
        self.tubes_channel[CHANNEL] = dbus.Interface(self.tubes_proxy, CHANNEL)
        self.tubes_channel[CHANNEL].GetInterfaces(
            reply_handler=self.__tubes_get_interfaces_reply_cb,
            error_handler=self.__error_handler_cb)

    def __tubes_get_interfaces_reply_cb(self, interfaces):
        for interface in interfaces:
            self.tubes_channel[interface] = dbus.Interface(
                self.tubes_proxy, interface)
        _logger.debug('%r: Tubes channel is ready' % (self))
        self._tubes_ready = True
        self._ready()

    def __tubes_error_handler_cb(self, error):
        if (error.get_dbus_name() ==
                'org.freedesktop.Telepathy.Error.NotImplemented'):
            self._tubes_supported = False
            self._ready()
        else:
            self._finished = True
            self.emit('finished', error)

    def __error_handler_cb(self, error):
        self._finished = True
        self.emit('finished', error)

    def _ready(self):
        if not self._text_ready or \
                (self._tubes_supported and not self._tubes_ready):
            return

        _logger.debug('%r: finished setting up channel' % self)

        self._add_self_to_channel()

    def __text_channel_group_flags_changed_cb(self, added, removed):
        _logger.debug(
            '__text_channel_group_flags_changed_cb %r %r' %
            (added, removed))
        self.text_channel_group_flags |= added
        self.text_channel_group_flags &= ~removed

    def _add_self_to_channel(self):
        # FIXME: cope with non-Group channels here if we want to support
        # non-OLPC-compatible IMs

        group = self.text_channel[CHANNEL_INTERFACE_GROUP]

        def got_all_members(members, local_pending, remote_pending):
            _logger.debug('got_all_members members %r local_pending %r '
                          'remote_pending %r' % (members, local_pending,
                                                 remote_pending))

            if self.text_channel_group_flags & \
                    CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES:
                self_handle = self.channel_self_handle
            else:
                self_handle = self._global_self_handle

            if self_handle in local_pending:
                _logger.debug('%r: We are in local pending - entering' % self)
                group.AddMembers([self_handle], '',
                                 reply_handler=lambda: None,
                                 error_handler=lambda e: self._join_failed_cb(
                                     e, 'got_all_members AddMembers'))

            if members:
                self.__text_channel_members_changed_cb('', members, (),
                                                       (), (), 0, 0)

        def got_group_flags(flags):
            self.text_channel_group_flags = flags
            # by the time we hook this, we need to know the group flags
            group.connect_to_signal('MembersChanged',
                                    self.__text_channel_members_changed_cb)

            # bootstrap by getting the current state. This is where we find
            # out whether anyone was lying to us in their PEP info
            group.GetAllMembers(reply_handler=got_all_members,
                                error_handler=self.__error_handler_cb)

        def got_self_handle(channel_self_handle):
            self.channel_self_handle = channel_self_handle
            group.connect_to_signal('GroupFlagsChanged',
                                    self.__text_channel_group_flags_changed_cb)
            group.GetGroupFlags(reply_handler=got_group_flags,
                                error_handler=self.__error_handler_cb)

        group.GetSelfHandle(reply_handler=got_self_handle,
                            error_handler=self.__error_handler_cb)

    def __text_channel_members_changed_cb(self, message, added, removed,
                                          local_pending, remote_pending,
                                          actor, reason):
        _logger.debug('__text_channel_members_changed_cb added %r removed %r '
                      'local_pending %r remote_pending %r channel_self_handle '
                      '%r' % (added, removed, local_pending, remote_pending,
                              self.channel_self_handle))

        if self.text_channel_group_flags & \
                CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES:
            self_handle = self.channel_self_handle
        else:
            self_handle = self._global_self_handle

        if self_handle not in added:
            return

        # Use RoomConfig1 to configure the text channel. If this
        # doesn't exist, fall-back on old-style PROPERTIES_INTERFACE.
        if CONN_INTERFACE_ROOM_CONFIG in self.text_channel:
            self.__update_room_config()
        elif PROPERTIES_INTERFACE in self.text_channel:
            self.text_channel[PROPERTIES_INTERFACE].ListProperties(
                reply_handler=self.__list_properties_cb,
                error_handler=self.__error_handler_cb)
        else:
            # FIXME: when does this codepath get hit?
            # It could be related to no property configuration being available
            # in the selected backend, or it could be called at some stage
            # of the protocol when properties aren't available yet.
            self._finished = True
            self.emit('finished', None)

    def __update_room_config(self):
        # FIXME: invite-only ought to be set on private activities; but
        # since only the owner can change invite-only, that would break
        # activity scope changes.
        props = {
            # otherwise buddy resolution breaks
            'Anonymous': False,
            # anyone who knows about the channel can join
            'InviteOnly': False,
            # vanish when there are no members
            'Persistent': False,
            # don't appear in server room lists
            'Private': True,
        }
        room_cfg = self.text_channel[CONN_INTERFACE_ROOM_CONFIG]
        room_cfg.UpdateConfiguration(props,
                                     reply_handler=self.__room_cfg_updated_cb,
                                     error_handler=self.__room_cfg_error_cb)

    def __room_cfg_updated_cb(self):
        self._finished = True
        self.emit('finished', None)

    def __room_cfg_error_cb(self, error):
        # If RoomConfig update fails, it's probably because we don't have
        # permission (e.g. we are not the session initiator). Thats OK -
        # ignore the failure and carry on.
        if (error.get_dbus_name() !=
                'org.freedesktop.Telepathy.Error.PermissionDenied'):
            logging.error("Error setting room configuration: %s", error)
        self._finished = True
        self.emit('finished', None)

    def __list_properties_cb(self, prop_specs):
        # FIXME: invite-only ought to be set on private activities; but
        # since only the owner can change invite-only, that would break
        # activity scope changes.
        props = {
            # otherwise buddy resolution breaks
            'anonymous': False,
            # anyone who knows about the channel can join
            'invite-only': False,
            # so non-owners can invite others
            'invite-restricted': False,
            # vanish when there are no members
            'persistent': False,
            # don't appear in server room lists
            'private': True,
        }
        props_to_set = []
        for ident, name, sig_, flags in prop_specs:
            value = props.pop(name, None)
            if value is not None:
                if flags & PROPERTY_FLAG_WRITE:
                    props_to_set.append((ident, value))
                # FIXME: else error, but only if we're creating the room?
        # FIXME: if props is nonempty, then we want to set props that aren't
        # supported here - raise an error?

        if props_to_set:
            self.text_channel[PROPERTIES_INTERFACE].SetProperties(
                props_to_set, reply_handler=self.__set_properties_cb,
                error_handler=self.__error_handler_cb)
        else:
            self._finished = True
            self.emit('finished', None)

    def __set_properties_cb(self):
        self._finished = True
        self.emit('finished', None)

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

"""UI interface to a buddy in the presence service

STABLE.
"""

import logging

import six
import gi
gi.require_version('TelepathyGLib', '0.12')
from gi.repository import GObject
import dbus

from sugar3.presence.connectionmanager import get_connection_manager
from sugar3.profile import get_color, get_nick_name

from gi.repository import TelepathyGLib

CONNECTION = TelepathyGLib.IFACE_CONNECTION
CONNECTION_INTERFACE_ALIASING = \
    TelepathyGLib.IFACE_CONNECTION_INTERFACE_ALIASING
CONNECTION_INTERFACE_CONTACTS = \
    TelepathyGLib.IFACE_CONNECTION_INTERFACE_CONTACTS

HANDLE_TYPE_CONTACT = TelepathyGLib.HandleType.CONTACT

CONN_INTERFACE_BUDDY_INFO = 'org.laptop.Telepathy.BuddyInfo'

_logger = logging.getLogger('sugar3.presence.buddy')


class BaseBuddy(GObject.GObject):
    """UI interface for a Buddy in the presence service

    Each buddy interface tracks a set of activities and properties
    that can be queried to provide UI controls for manipulating
    the presence interface.

    Properties Dictionary:
        'key': public key,
        'nick': nickname ,
        'color': color (XXX what format),
        'current-activity': (XXX dbus path?),
        'owner': (XXX dbus path?),
    """

    __gtype_name__ = 'PresenceBaseBuddy'

    __gsignals__ = {
        'joined-activity': (GObject.SignalFlags.RUN_FIRST, None,
                            ([GObject.TYPE_PYOBJECT])),
        'left-activity': (GObject.SignalFlags.RUN_FIRST, None,
                          ([GObject.TYPE_PYOBJECT])),
        'property-changed': (GObject.SignalFlags.RUN_FIRST, None,
                             ([GObject.TYPE_PYOBJECT])),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self._key = None
        self._nick = None
        self._color = None
        self._current_activity = None
        self._owner = False
        self._ip4_address = None
        self._tags = None

    def get_key(self):
        return self._key

    def set_key(self, key):
        self._key = key

    key = GObject.Property(type=str, getter=get_key, setter=set_key)

    def get_nick(self):
        return self._nick

    def set_nick(self, nick):
        self._nick = nick

    nick = GObject.Property(type=str, getter=get_nick, setter=set_nick)

    def get_color(self):
        return self._color

    def set_color(self, color):
        self._color = color

    color = GObject.Property(type=str, getter=get_color, setter=set_color)

    def get_current_activity(self):
        if self._current_activity is None:
            return None
        for activity in list(self._activities.values()):
            if activity.props.id == self._current_activity:
                return activity
        return None

    current_activity = GObject.Property(type=object,
                                        getter=get_current_activity)

    def get_owner(self):
        return self._owner

    def set_owner(self, owner):
        self._owner = owner

    owner = GObject.Property(type=bool, getter=get_owner, setter=set_owner,
                             default=False)

    def get_ip4_address(self):
        return self._ip4_address

    def set_ip4_address(self, ip4_address):
        self._ip4_address = ip4_address

    ip4_address = GObject.Property(type=str, getter=get_ip4_address,
                                   setter=set_ip4_address)

    def get_tags(self):
        return self._tags

    def set_tags(self, tags):
        self._tags = tags

    tags = GObject.Property(type=str, getter=get_tags, setter=set_tags)

    def object_path(self):
        """Retrieve our dbus object path"""
        return None


class Buddy(BaseBuddy):
    __gtype_name__ = 'PresenceBuddy'

    def __init__(self, account_path, contact_id):
        _logger.debug('Buddy.__init__')
        BaseBuddy.__init__(self)

        self._account_path = account_path
        self.contact_id = contact_id
        self.contact_handle = None

        connection_manager = get_connection_manager()
        connection = connection_manager.get_connection(account_path)

        connection_name = connection.object_path.replace('/', '.')[1:]

        bus = dbus.SessionBus()
        obj = bus.get_object(connection_name, connection.object_path)
        handles = obj.RequestHandles(HANDLE_TYPE_CONTACT, [self.contact_id],
                                     dbus_interface=CONNECTION)
        self.contact_handle = handles[0]

        if six.PY2:
            self._get_properties_call = bus.call_async(
                connection_name,
                connection.object_path,
                CONN_INTERFACE_BUDDY_INFO,
                'GetProperties',
                'u',
                (self.contact_handle,),
                reply_handler=self.__got_properties_cb,
                error_handler=self.__error_handler_cb,
                utf8_strings=True,
                byte_arrays=True)
        else:
            self._get_properties_call = bus.call_async(
                connection_name,
                connection.object_path,
                CONN_INTERFACE_BUDDY_INFO,
                'GetProperties',
                'u',
                (self.contact_handle,),
                reply_handler=self.__got_properties_cb,
                error_handler=self.__error_handler_cb,
                byte_arrays=True)

        self._get_attributes_call = bus.call_async(
            connection_name,
            connection.object_path,
            CONNECTION_INTERFACE_CONTACTS,
            'GetContactAttributes',
            'auasb',
            ([self.contact_handle], [CONNECTION_INTERFACE_ALIASING],
             False),
            reply_handler=self.__got_attributes_cb,
            error_handler=self.__error_handler_cb)

    def __got_properties_cb(self, properties):
        _logger.debug('__got_properties_cb %r', properties)
        self._get_properties_call = None
        self._update_properties(properties)

    def __got_attributes_cb(self, attributes):
        _logger.debug('__got_attributes_cb %r', attributes)
        self._get_attributes_call = None
        self._update_attributes(attributes[self.contact_handle])

    def __error_handler_cb(self, error):
        _logger.debug('__error_handler_cb %r', error)

    def __properties_changed_cb(self, new_props):
        _logger.debug('%r: Buddy properties changed to %r', self, new_props)
        self._update_properties(new_props)

    def _update_properties(self, properties):
        if 'key' in properties:
            self.props.key = properties['key']
        if 'color' in properties:
            self.props.color = properties['color']
        if 'current-activity' in properties:
            self.props.current_activity = properties['current-activity']
        if 'owner' in properties:
            self.props.owner = properties['owner']
        if 'ip4-address' in properties:
            self.props.ip4_address = properties['ip4-address']
        if 'tags' in properties:
            self.props.tags = properties['tags']

    def _update_attributes(self, attributes):
        nick_key = CONNECTION_INTERFACE_ALIASING + '/alias'
        if nick_key in attributes:
            self.props.nick = attributes[nick_key]

    def do_get_property(self, pspec):
        if pspec.name == 'nick' and self._get_attributes_call is not None:
            _logger.debug('%r: Blocking on GetContactAttributes() because '
                          'someone wants property nick', self)
            self._get_attributes_call.block()
        elif pspec.name != 'nick' and self._get_properties_call is not None:
            _logger.debug('%r: Blocking on GetProperties() because someone '
                          'wants property %s', self, pspec.name)
            self._get_properties_call.block()

        return BaseBuddy.do_get_property(self, pspec)


class Owner(BaseBuddy):

    __gtype_name__ = 'PresenceOwner'

    def __init__(self):
        BaseBuddy.__init__(self)

        self.props.nick = get_nick_name()
        self.props.color = get_color().to_string()

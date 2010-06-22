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

"""UI interface to a buddy in the presence service

STABLE.
"""

import logging

import gobject
import gtk
import dbus
import gconf
from telepathy.interfaces import CONNECTION_INTERFACE_ALIASING, \
                                 CONNECTION_INTERFACE_CONTACTS

CONN_INTERFACE_BUDDY_INFO = 'org.laptop.Telepathy.BuddyInfo'

_logger = logging.getLogger('sugar.presence.buddy')


class BaseBuddy(gobject.GObject):
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
        'icon': (XXX pixel data for an icon?)
    See __gproperties__
    """

    __gtype_name__ = 'PresenceBaseBuddy'

    __gsignals__ = {
        'icon-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'joined-activity': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
            ([gobject.TYPE_PYOBJECT])),
        'left-activity': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
            ([gobject.TYPE_PYOBJECT])),
        'property-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
            ([gobject.TYPE_PYOBJECT])),
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._key = None
        self._icon = None
        self._nick = None
        self._color = None
        self._current_activity = None
        self._owner = False
        self._ip4_address = None
        self._tags = None

    def destroy(self):
        self._icon_changed_signal.remove()
        self._joined_activity_signal.remove()
        self._left_activity_signal.remove()
        self._property_changed_signal.remove()

    def _get_properties_helper(self):
        """Retrieve the Buddy's property dictionary from the service object
        """
        props = self._buddy.GetProperties(byte_arrays=True)
        if not props:
            return {}
        return props

    def get_key(self):
        return self._key

    def set_key(self, key):
        self._key = key

    key = gobject.property(type=str, getter=get_key, setter=set_key)

    def get_icon(self):
        raise NotImplementedError()

    icon = gobject.property(type=str, getter=get_icon)

    def get_nick(self):
        return self._nick

    def set_nick(self, nick):
        self._nick = nick

    nick = gobject.property(type=str, getter=get_nick, setter=set_nick)

    def get_color(self):
        return self._color

    def set_color(self, color):
        self._color = color

    color = gobject.property(type=str, getter=get_color, setter=set_color)

    def get_current_activity(self):
        if self._current_activity is None:
            return None
        for activity in self._activities.values():
            if activity.props.id == self._current_activity:
                return activity
        return None

    current_activity = gobject.property(type=object, getter=get_current_activity)

    def get_owner(self):
        return self._owner

    def set_owner(self, owner):
        self._owner = owner

    owner = gobject.property(type=bool, getter=get_owner, setter=set_owner, default=False)

    def get_ip4_address(self):
        return self._ip4_address

    def set_ip4_address(self, ip4_address):
        self._ip4_address = ip4_address

    ip4_address = gobject.property(type=str, getter=get_ip4_address, setter=set_ip4_address)

    def get_tags(self):
        return self._tags

    def set_tags(self, tags):
        self._tags = tags

    tags = gobject.property(type=str, getter=get_tags, setter=set_tags)

    def object_path(self):
        """Retrieve our dbus object path"""
        return self._object_path

    def _emit_icon_changed_signal(self, icon_data):
        """Emit GObject signal when icon has changed"""
        self._icon = str(icon_data)
        self.emit('icon-changed')
        return False

    def __icon_changed_cb(self, icon_data):
        """Handle dbus signal by emitting a GObject signal"""
        gobject.idle_add(self._emit_icon_changed_signal, icon_data)

    def __emit_joined_activity_signal(self, object_path):
        """Emit activity joined signal with Activity object"""
        self.emit('joined-activity', self._ps_new_object(object_path))
        return False

    def __joined_activity_cb(self, object_path):
        """Handle dbus signal by emitting a GObject signal

        Stores the activity in activities dictionary as well
        """
        if not self._activities.has_key(object_path):
            self._activities[object_path] = self._ps_new_object(object_path)
        gobject.idle_add(self._emit_joined_activity_signal, object_path)

    def _emit_left_activity_signal(self, object_path):
        """Emit activity left signal with Activity object

        XXX this calls self._ps_new_object instead of self._ps_del_object,
            which would seem to be the incorrect callback?
        """
        self.emit('left-activity', self._ps_new_object(object_path))
        return False

    def __left_activity_cb(self, object_path):
        """Handle dbus signal by emitting a GObject signal

        Also removes from the activities dictionary
        """
        if self._activities.has_key(object_path):
            del self._activities[object_path]
        gobject.idle_add(self._emit_left_activity_signal, object_path)

    def _handle_property_changed_signal(self, prop_list):
        """Emit property-changed signal with property dictionary

        Generates a property-changed signal with the results of
        _get_properties_helper()
        """
        self._properties = self._get_properties_helper()
        # FIXME: don't leak unexposed property names
        self.emit('property-changed', prop_list)
        return False

    def __property_changed_cb(self, prop_list):
        """Handle dbus signal by emitting a GObject signal"""
        gobject.idle_add(self._handle_property_changed_signal, prop_list)

    def get_icon_pixbuf(self):
        """Retrieve Buddy's icon as a GTK pixel buffer

        XXX Why aren't the icons coming in as SVG?
        """
        if self.props.icon and len(self.props.icon):
            pbl = gtk.gdk.PixbufLoader()
            pbl.write(self.props.icon)
            pbl.close()
            return pbl.get_pixbuf()
        else:
            return None

    def get_joined_activities(self):
        """Retrieve the set of all activities which this buddy has joined

        Uses the GetJoinedActivities method on the service
        object to produce object paths, wraps each in an
        Activity object.

        returns list of presence Activity objects
        """
        try:
            resp = self._buddy.GetJoinedActivities()
        except dbus.exceptions.DBusException:
            return []
        acts = []
        for item in resp:
            acts.append(self._ps_new_object(item))
        return acts


class Buddy(BaseBuddy):
    __gtype_name__ = 'PresenceBuddy'
    def __init__(self, connection, contact_handle):
        BaseBuddy.__init__(self)

        self._contact_handle = contact_handle

        bus = dbus.SessionBus()
        self._get_properties_call = bus.call_async(
                connection.requested_bus_name,
                connection.object_path,
                CONN_INTERFACE_BUDDY_INFO,
                'GetProperties',
                'u',
                (self._contact_handle,),
                reply_handler=self.__got_properties_cb,
                error_handler=self.__error_handler_cb,
                utf8_strings=True,
                byte_arrays=True)

        self._get_attributes_call = bus.call_async(
                connection.requested_bus_name,
                connection.object_path,
                CONNECTION_INTERFACE_CONTACTS,
                'GetContactAttributes',
                'auasb',
                ([self._contact_handle], [CONNECTION_INTERFACE_ALIASING], False),
                reply_handler=self.__got_attributes_cb,
                error_handler=self.__error_handler_cb)

    def __got_properties_cb(self, properties):
        _logger.debug('__got_properties_cb', properties)
        self._get_properties_call = None
        self._update_properties(properties)

    def __got_attributes_cb(self, attributes):
        _logger.debug('__got_attributes_cb', attributes)
        self._get_attributes_call = None
        self._update_attributes(attributes[self._contact_handle])

    def __error_handler_cb(self, error):
        _logger.debug('__error_handler_cb', error)

    def __properties_changed_cb(self, new_props):
        _logger.debug('%r: Buddy properties changed to %r', self, new_props)
        self._update_properties(new_props)

    def _update_properties(self, properties):
        if 'key' in properties:
            self.props.key = properties['key']
        if 'icon' in properties:
            self.props.icon = properties['icon']
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
        if self._get_properties_call is not None:
            _logger.debug('%r: Blocking on GetProperties() because someone '
                          'wants property %s', self, pspec.name)
            self._get_properties_call.block()

        return BaseBuddy.do_get_property(self, pspec)


class Owner(BaseBuddy):

    __gtype_name__ = 'PresenceOwner'

    def __init__(self):
        BaseBuddy.__init__(self)

        client = gconf.client_get_default()
        self.props.nick = client.get_string("/desktop/sugar/user/nick")
        self.props.color = client.get_string("/desktop/sugar/user/color")

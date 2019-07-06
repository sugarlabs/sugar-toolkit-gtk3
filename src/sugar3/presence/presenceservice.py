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

"""
STABLE.
"""

import logging
import dbus
import dbus.exceptions
from dbus import PROPERTIES_IFACE

from sugar3.presence.buddy import Buddy, Owner
from sugar3.presence.activity import Activity
from sugar3.presence.connectionmanager import get_connection_manager

from gi.repository import GObject
from gi.repository import TelepathyGLib

_logger = logging.getLogger('sugar3.presence.presenceservice')

ACCOUNT_MANAGER_SERVICE = TelepathyGLib.ACCOUNT_MANAGER_BUS_NAME
ACCOUNT_MANAGER_PATH = TelepathyGLib.ACCOUNT_MANAGER_OBJECT_PATH
ACCOUNT_MANAGER = TelepathyGLib.IFACE_ACCOUNT_MANAGER

ACCOUNT = TelepathyGLib.IFACE_ACCOUNT

HANDLE_TYPE_CONTACT = TelepathyGLib.HandleType.CONTACT

CONNECTION = TelepathyGLib.IFACE_CONNECTION

CONN_INTERFACE_ACTIVITY_PROPERTIES = 'org.laptop.Telepathy.ActivityProperties'


class PresenceService(GObject.GObject):
    """Provides simplified access to the Telepathy framework to activities"""
    __gsignals__ = {
        'activity-shared': (GObject.SignalFlags.RUN_FIRST, None,
                            ([GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT,
                              GObject.TYPE_PYOBJECT])),
    }

    def __init__(self):
        """Initialise the service and attempt to connect to events
        """
        GObject.GObject.__init__(self)

        self._activity_cache = None
        self._buddy_cache = {}

    def get_activity(self, activity_id, warn_if_none=True):
        """Retrieve single Activity object for the given unique id

        activity_id -- unique ID for the activity

        returns single Activity object or None if the activity
            is not found using GetActivityById on the service
        """
        if self._activity_cache is not None:
            if self._activity_cache.props.id != activity_id:
                raise RuntimeError('Activities can only access their own'
                                   ' shared instance')
            return self._activity_cache
        else:
            connection_manager = get_connection_manager()
            connections_per_account = \
                connection_manager.get_connections_per_account()
            for account_path, connection in list(
                    connections_per_account.items()):
                if not connection.connected:
                    continue
                logging.debug('Calling GetActivity on %s' % account_path)
                try:
                    room_handle = connection.connection.GetActivity(
                        activity_id,
                        dbus_interface=CONN_INTERFACE_ACTIVITY_PROPERTIES)
                except dbus.exceptions.DBusException as e:
                    name = 'org.freedesktop.Telepathy.Error.NotAvailable'
                    if e.get_dbus_name() == name:
                        logging.debug("There's no shared activity with the id "
                                      "%s" % activity_id)
                    elif e.get_dbus_name() == \
                            'org.freedesktop.DBus.Error.UnknownMethod':
                        logging.warning(
                            'Telepathy Account %r does not support '
                            'Sugar collaboration', account_path)
                    else:
                        raise
                else:
                    activity = Activity(account_path, connection.connection,
                                        room_handle=room_handle)
                    self._activity_cache = activity
                    return activity

        return None

    def get_activity_by_handle(self, connection_path, room_handle):
        if self._activity_cache is not None:
            if self._activity_cache.room_handle != room_handle:
                raise RuntimeError('Activities can only access their own'
                                   ' shared instance')
            return self._activity_cache
        else:
            connection_manager = get_connection_manager()
            account_path = \
                connection_manager.get_account_for_connection(connection_path)

            connection_name = connection_path.replace('/', '.')[1:]
            bus = dbus.SessionBus()
            connection = bus.get_object(connection_name, connection_path)
            activity = Activity(account_path, connection,
                                room_handle=room_handle)
            self._activity_cache = activity
            return activity

    def get_buddy(self, account_path, contact_id):
        if (account_path, contact_id) in self._buddy_cache:
            return self._buddy_cache[(account_path, contact_id)]

        buddy = Buddy(account_path, contact_id)
        self._buddy_cache[(account_path, contact_id)] = buddy
        return buddy

    # DEPRECATED
    def get_buddy_by_telepathy_handle(self, tp_conn_name, tp_conn_path,
                                      handle):
        """Retrieve single Buddy object for the given public key

        :Parameters:
            `tp_conn_name` : str
                The well-known bus name of a Telepathy connection
            `tp_conn_path` : dbus.ObjectPath
                The object path of the Telepathy connection
            `handle` : int or long
                The handle of a Telepathy contact on that connection,
                of type HANDLE_TYPE_CONTACT. This may not be a
                channel-specific handle.
        :Returns: the Buddy object, or None if the buddy is not found
        """

        bus = dbus.Bus()
        obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, ACCOUNT_MANAGER_PATH)
        account_manager = dbus.Interface(obj, ACCOUNT_MANAGER)
        account_paths = account_manager.Get(ACCOUNT_MANAGER, 'ValidAccounts',
                                            dbus_interface=PROPERTIES_IFACE)
        for account_path in account_paths:
            obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, account_path)
            connection_path = obj.Get(ACCOUNT, 'Connection')
            if connection_path == tp_conn_path:
                connection_name = connection_path.replace('/', '.')[1:]
                connection = bus.get_object(connection_name, connection_path)
                contact_ids = connection.InspectHandles(
                    HANDLE_TYPE_CONTACT,
                    [handle],
                    dbus_interface=CONNECTION)
                return self.get_buddy(account_path, contact_ids[0])

        raise ValueError('Unknown buddy in connection %s with handle %d' %
                         (tp_conn_path, handle))

    def get_owner(self):
        """Retrieves the laptop Buddy object."""
        return Owner()

    def __share_activity_cb(self, activity):
        """Finish sharing the activity
        """
        self.emit('activity-shared', True, activity, None)

    def __share_activity_error_cb(self, activity, error):
        """Notify with GObject event of unsuccessful sharing of activity
        """
        self.emit('activity-shared', False, activity, error)

    def share_activity(self, activity, properties=None, private=True):
        if properties is None:
            properties = {}

        if 'id' not in properties:
            properties['id'] = activity.get_id()

        if 'type' not in properties:
            properties['type'] = activity.get_bundle_id()

        if 'name' not in properties:
            properties['name'] = activity.metadata.get('title', None)

        if 'color' not in properties:
            properties['color'] = activity.metadata.get('icon-color', None)

        properties['private'] = private

        if self._activity_cache is not None:
            raise ValueError('Activity %s is already tracked' %
                             activity.get_id())

        connection_manager = get_connection_manager()
        account_path, connection = \
            connection_manager.get_preferred_connection()

        if connection is None:
            self.emit('activity-shared', False, None,
                      'No active connection available')
            return

        shared_activity = Activity(account_path, connection,
                                   properties=properties)
        self._activity_cache = shared_activity

        if shared_activity.props.joined:
            raise RuntimeError('Activity %s is already shared.' %
                               activity.props.id)

        shared_activity.share(self.__share_activity_cb,
                              self.__share_activity_error_cb)

    def get_preferred_connection(self):
        """Gets the preferred telepathy connection object that an activity
        should use when talking directly to telepathy

        returns the bus name and the object path of the Telepathy connection
        """
        manager = get_connection_manager()
        account_path, connection = manager.get_preferred_connection()
        if connection is None:
            return None
        else:
            return connection.requested_bus_name, connection.object_path

    # DEPRECATED
    def get(self, object_path):
        raise NotImplementedError()

    # DEPRECATED
    def get_activities(self):
        raise NotImplementedError()

    # DEPRECATED
    def get_activities_async(self, reply_handler=None, error_handler=None):
        raise NotImplementedError()

    # DEPRECATED
    def get_buddies(self):
        raise NotImplementedError()

    # DEPRECATED
    def get_buddies_async(self, reply_handler=None, error_handler=None):
        raise NotImplementedError()


_ps = None


def get_instance(allow_offline_iface=False):
    """Retrieve this process' view of the PresenceService"""
    global _ps
    if not _ps:
        _ps = PresenceService()
    return _ps

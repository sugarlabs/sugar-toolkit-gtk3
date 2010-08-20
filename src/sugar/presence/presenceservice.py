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

import gobject
import dbus
import dbus.exceptions
import dbus.glib
from dbus import PROPERTIES_IFACE

from sugar.presence.buddy import Buddy, Owner
from sugar.presence.activity import Activity
from sugar.presence.connectionmanager import get_connection_manager

from telepathy.interfaces import ACCOUNT, \
                                 ACCOUNT_MANAGER, \
                                 CONNECTION
from telepathy.constants import HANDLE_TYPE_CONTACT

_logger = logging.getLogger('sugar.presence.presenceservice')

ACCOUNT_MANAGER_SERVICE = 'org.freedesktop.Telepathy.AccountManager'
ACCOUNT_MANAGER_PATH = '/org/freedesktop/Telepathy/AccountManager'

class PresenceService(gobject.GObject):
    """Provides simplified access to the Telepathy framework to activities"""
    __gsignals__ = {
        'activity-shared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT,
                          gobject.TYPE_PYOBJECT])),
    }

    def __init__(self):
        """Initialise the service and attempt to connect to events
        """
        gobject.GObject.__init__(self)

        self._activity_cache = None
        self._buddy_cache = {}

    def _new_object(self, object_path):
        """Turn new object path into (cached) Buddy/Activity instance

        object_path -- full dbus path of the new object, must be
            prefixed with either of _PS_BUDDY_OP or _PS_ACTIVITY_OP

        Note that this method is called throughout the class whenever
        the representation of the object is required, it is not only
        called when the object is first discovered.  The point is to only have
        _one_ Python object for any D-Bus object represented by an object path,
        effectively wrapping the D-Bus object in a single Python GObject.

        returns presence Buddy or Activity representation
        """
        obj = None
        try:
            obj = self._objcache[object_path]
            _logger.debug('Reused proxy %r', obj)
        except KeyError:
            if object_path.startswith(self._PS_BUDDY_OP):
                obj = Buddy(self._bus, self._new_object,
                        self._del_object, object_path)
            elif object_path.startswith(self._PS_ACTIVITY_OP):
                obj = Activity(self._bus, self._new_object,
                        self._del_object, object_path)
                try:
                    # Pre-fill the activity's ID
                    activity_id = obj.props.id
                except dbus.exceptions.DBusException:
                    logging.debug('Cannot get the activity ID')
            else:
                raise RuntimeError("Unknown object type")
            self._objcache[object_path] = obj
            _logger.debug('Created proxy %r', obj)
        return obj

    def _have_object(self, object_path):
        return object_path in self._objcache.keys()

    def _del_object(self, object_path):
        """Fully remove an object from the object cache when
           it's no longer needed.
        """
        del self._objcache[object_path]

    def get(self, object_path):
        """Return the Buddy or Activity object corresponding to the given
        D-Bus object path.
        """
        return self._new_object(object_path)

    def get_activities(self):
        """Retrieve set of all activities from service

        returns list of Activity objects for all object paths
            the service reports exist (using GetActivities)
        """
        resp = self._ps.GetActivities()
        acts = []
        for item in resp:
            acts.append(self._new_object(item))
        return acts

    def _get_activities_cb(self, reply_handler, resp):
        acts = []
        for item in resp:
            acts.append(self._new_object(item))

        reply_handler(acts)

    def _get_activities_error_cb(self, error_handler, e):
        if error_handler:
            error_handler(e)
        else:
            _logger.warn('Unable to retrieve activity-list from presence '
                'service: %s', e)

    def get_activities_async(self, reply_handler=None, error_handler=None):
        """Retrieve set of all activities from service asyncronously
        """

        if not reply_handler:
            logging.error('Function get_activities_async called without' \
                          'a reply handler. Can not run.')
            return

        self._ps.GetActivities(
             reply_handler=lambda resp: \
                    self._get_activities_cb(reply_handler, resp),
             error_handler=lambda e: \
                    self._get_activities_error_cb(error_handler, e))

    def get_activity(self, activity_id, warn_if_none=True):
        """Retrieve single Activity object for the given unique id

        activity_id -- unique ID for the activity

        returns single Activity object or None if the activity
            is not found using GetActivityById on the service
        """
        if self._activity_cache is not None:
            if self._activity_cache.props.id != activity_id:
                raise RuntimeError('Activities can only access their own shared'
                                   'instance')
            return self._activity_cache
        else:
            connection_manager = get_connection_manager()
            connections_per_account = \
                    connection_manager.get_connections_per_account()
            for account_path, connection in connections_per_account.items():
                if not connection.connected:
                    continue
                logging.debug("Calling GetActivity on %s", account_path)
                try:
                    room_handle = connection.connection.GetActivity(activity_id)
                except dbus.exceptions.DBusException, e:
                    name = 'org.freedesktop.Telepathy.Error.NotAvailable'
                    if e.get_dbus_name() == name:
                        logging.debug("There's no shared activity with the id "
                                      "%s", activity_id)
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
                raise RuntimeError('Activities can only access their own shared'
                                   'instance')
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

    def get_buddies(self):
        """Retrieve set of all buddies from service

        returns list of Buddy objects for all object paths
            the service reports exist (using GetBuddies)
        """
        try:
            resp = self._ps.GetBuddies()
        except dbus.exceptions.DBusException:
            _logger.exception('Unable to retrieve buddy-list from presence '
                'service')
            return []
        else:
            buddies = []
            for item in resp:
                buddies.append(self._new_object(item))
            return buddies

    def _get_buddies_cb(self, reply_handler, resp):
        buddies = []
        for item in resp:
            buddies.append(self._new_object(item))

        reply_handler(buddies)

    def _get_buddies_error_cb(self, error_handler, e):
        if error_handler:
            error_handler(e)
        else:
            _logger.warn('Unable to retrieve buddy-list from presence '
                'service: %s', e)

    def get_buddies_async(self, reply_handler=None, error_handler=None):
        """Retrieve set of all buddies from service asyncronously
        """

        if not reply_handler:
            logging.error('Function get_buddies_async called without' \
                          'a reply handler. Can not run.')
            return

        self._ps.GetBuddies(
             reply_handler=lambda resp: \
                    self._get_buddies_cb(reply_handler, resp),
             error_handler=lambda e: \
                    self._get_buddies_error_cb(error_handler, e))

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
                contact_ids = connection.InspectHandles(HANDLE_TYPE_CONTACT,
                        [handle],
                        dbus_interface=CONNECTION)
                return self.get_buddy(account_path, contact_ids[0])

        raise ValueError('Unknown buddy in connection %s with handle %d',
                         tp_conn_path, handle)

    def get_owner(self):
        """Retrieves the laptop Buddy object."""
        return Owner()

    def __share_activity_cb(self, activity):
        """Finish sharing the activity
        """
        self.emit("activity-shared", True, activity, None)

    def __share_activity_error_cb(self, activity, error):
        """Notify with GObject event of unsuccessful sharing of activity
        """
        self.emit("activity-shared", False, activity, error)

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
            raise ValueError('Activity %s is already tracked',
                             activity.get_id())

        connection_manager = get_connection_manager()
        account_path, connection = \
                connection_manager.get_preferred_connection()
        shared_activity = Activity(account_path, connection,
                                   properties=properties)
        self._activity_cache = shared_activity

        """
        if shared_activity.props.joined:
            raise RuntimeError('Activity %s is already shared.' %
                               activity.get_id())
        """

        shared_activity.share(self.__share_activity_cb,
                              self.__share_activity_error_cb)

    def get_preferred_connection(self):
        """Gets the preferred telepathy connection object that an activity
        should use when talking directly to telepathy

        returns the bus name and the object path of the Telepathy connection
        """
        connection_manager = get_connection_manager()
        account_path, connection = connection_manager.get_preferred_connection()
        if connection is None:
            return None
        else:
            return connection.requested_bus_name, connection.object_path


_ps = None


def get_instance(allow_offline_iface=False):
    """Retrieve this process' view of the PresenceService"""
    global _ps
    if not _ps:
        _ps = PresenceService()
    return _ps

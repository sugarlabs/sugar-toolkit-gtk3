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
UNSTABLE. It should really be internal to the sugar3.presence package.
"""

from functools import partial

import dbus
from dbus import PROPERTIES_IFACE

from gi.repository import TelepathyGLib

ACCOUNT_MANAGER_SERVICE = TelepathyGLib.ACCOUNT_MANAGER_BUS_NAME
ACCOUNT_MANAGER_PATH = TelepathyGLib.ACCOUNT_MANAGER_OBJECT_PATH
ACCOUNT_MANAGER = TelepathyGLib.IFACE_ACCOUNT_MANAGER

ACCOUNT = TelepathyGLib.IFACE_ACCOUNT

HANDLE_TYPE_CONTACT = TelepathyGLib.HandleType.CONTACT

CONNECTION = TelepathyGLib.IFACE_CONNECTION

CONNECTION_STATUS_CONNECTED = TelepathyGLib.ConnectionStatus.CONNECTED


class Connection(object):
    def __init__(self, account_path, connection):
        self.account_path = account_path
        self.connection = connection
        self.connected = False


class ConnectionManager(object):
    """Track available telepathy connections"""

    def __init__(self):
        self._connections_per_account = {}

        bus = dbus.SessionBus()
        obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, ACCOUNT_MANAGER_PATH)
        account_manager = dbus.Interface(obj, ACCOUNT_MANAGER)
        account_paths = account_manager.Get(ACCOUNT_MANAGER, 'ValidAccounts',
                                            dbus_interface=PROPERTIES_IFACE)
        for account_path in account_paths:
            obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, account_path)
            obj.connect_to_signal('AccountPropertyChanged',
                                  partial(self.__account_property_changed_cb,
                                          account_path))
            connection_path = obj.Get(ACCOUNT, 'Connection')
            if connection_path != '/':
                self._track_connection(account_path, connection_path)

    def __account_property_changed_cb(self, account_path, properties):
        if 'Connection' not in properties:
            return
        if properties['Connection'] == '/':
            if account_path in self._connections_per_account:
                del self._connections_per_account[account_path]
        else:
            self._track_connection(account_path, properties['Connection'])

    def _track_connection(self, account_path, connection_path):
        connection_name = connection_path.replace('/', '.')[1:]
        bus = dbus.SessionBus()
        connection = bus.get_object(connection_name, connection_path)
        connection.connect_to_signal('StatusChanged',
                                     partial(self.__status_changed_cb,
                                             account_path))
        self._connections_per_account[account_path] = \
            Connection(account_path, connection)

        account = bus.get_object(ACCOUNT_MANAGER_SERVICE, account_path)
        status = account.Get(ACCOUNT, 'ConnectionStatus')
        if status == CONNECTION_STATUS_CONNECTED:
            self._connections_per_account[account_path].connected = True
        else:
            self._connections_per_account[account_path].connected = False

    def __status_changed_cb(self, account_path, status, reason):
        if status == CONNECTION_STATUS_CONNECTED:
            self._connections_per_account[account_path].connected = True
        else:
            self._connections_per_account[account_path].connected = False

    def get_preferred_connection(self):
        best_connection = None, None
        for account_path, connection in list(
                self._connections_per_account.items()):
            if 'salut' in account_path and connection.connected:
                best_connection = account_path, connection.connection
            elif 'gabble' in account_path and connection.connected:
                best_connection = account_path, connection.connection
                break
        return best_connection

    def get_connection(self, account_path):
        return self._connections_per_account[account_path].connection

    def get_connections_per_account(self):
        return self._connections_per_account

    def get_account_for_connection(self, connection_path):
        for account_path, connection in list(
                self._connections_per_account.items()):
            if connection.connection.object_path == connection_path:
                return account_path
        return None


_connection_manager = None


def get_connection_manager():
    global _connection_manager
    if not _connection_manager:
        _connection_manager = ConnectionManager()
    return _connection_manager

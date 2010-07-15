import logging

import dbus
from dbus import PROPERTIES_IFACE
from telepathy.interfaces import ACCOUNT, \
                                 ACCOUNT_MANAGER

ACCOUNT_MANAGER_SERVICE = 'org.freedesktop.Telepathy.AccountManager'
ACCOUNT_MANAGER_PATH = '/org/freedesktop/Telepathy/AccountManager'

class ConnectionManager(object):
    def __init__(self):
        self._connections_per_account = {}

        bus = dbus.SessionBus()
        obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, ACCOUNT_MANAGER_PATH)
        account_manager = dbus.Interface(obj, ACCOUNT_MANAGER)

        logging.info('KILL_PS listen for accounts coming and going')
        #account_manager.connect_to_signal('AccountValidityChanged',
        #    self.__account_validity_changed_cb)

        account_paths = account_manager.Get(ACCOUNT_MANAGER, 'ValidAccounts',
                                            dbus_interface=PROPERTIES_IFACE)
        for account_path in account_paths:
            obj = bus.get_object(ACCOUNT_MANAGER_SERVICE, account_path)
            #obj.connect_to_signal('AccountPropertyChanged',
            #                      self.__account_property_changed_cb)
            connection_path = obj.Get(ACCOUNT, 'Connection')
            if connection_path == '/':
                continue

            connection_name = connection_path.replace('/', '.')[1:]
            connection = bus.get_object(connection_name, connection_path)
            self._connections_per_account[account_path] = connection

    def get_preferred_connection(self):
        best_connection = None, None
        for account_path, connection in self._connections_per_account.items():
            if 'salut' in connection.object_path:
                best_connection = account_path, connection
            elif 'gabble' in connection.object_path:
                best_connection = account_path, connection
                break
        return best_connection

    def get_connection(self, account_path):
        return self._connections_per_account[account_path]

    def get_connections_per_account(self):
        return self._connections_per_account

    def get_account_for_connection(self, connection_path):
        for account_path, connection in self._connections_per_account.items():
            if connection.object_path == connection_path:
                return account_path
        return None

_connection_manager = None

def get_connection_manager():
    global _connection_manager
    if not _connection_manager:
        _connection_manager = ConnectionManager()
    return _connection_manager

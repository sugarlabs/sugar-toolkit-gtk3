# Copyright (C) 2007, One Laptop Per Child
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

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
import dbus

from sugar3.datastore import datastore


J_DBUS_SERVICE = 'org.laptop.Journal'
J_DBUS_INTERFACE = 'org.laptop.Journal'
J_DBUS_PATH = '/org/laptop/Journal'


class ObjectChooser(object):

    def __init__(self, parent=None, what_filter=None):
        if parent is None:
            parent_xid = 0
        elif hasattr(parent, 'get_window') and hasattr(parent.get_window(),
                                                       'get_xid'):
            parent_xid = parent.get_window().get_xid()
        else:
            parent_xid = parent

        self._parent_xid = parent_xid
        self._main_loop = None
        self._object_id = None
        self._bus = None
        self._chooser_id = None
        self._response_code = Gtk.ResponseType.NONE
        self._what_filter = what_filter

    def run(self):
        self._object_id = None

        self._main_loop = GObject.MainLoop()

        self._bus = dbus.SessionBus(mainloop=self._main_loop)
        self._bus.add_signal_receiver(
            self.__name_owner_changed_cb,
            signal_name='NameOwnerChanged',
            dbus_interface='org.freedesktop.DBus',
            arg0=J_DBUS_SERVICE)

        obj = self._bus.get_object(J_DBUS_SERVICE, J_DBUS_PATH)
        journal = dbus.Interface(obj, J_DBUS_INTERFACE)
        journal.connect_to_signal('ObjectChooserResponse',
                                  self.__chooser_response_cb)
        journal.connect_to_signal('ObjectChooserCancelled',
                                  self.__chooser_cancelled_cb)

        if self._what_filter is None:
            what_filter = ''
        else:
            what_filter = self._what_filter

        self._chooser_id = journal.ChooseObject(self._parent_xid, what_filter)

        Gdk.threads_leave()
        try:
            self._main_loop.run()
        finally:
            Gdk.threads_enter()
        self._main_loop = None

        return self._response_code

    def get_selected_object(self):
        if self._object_id is None:
            return None
        else:
            return datastore.get(self._object_id)

    def destroy(self):
        self._cleanup()

    def _cleanup(self):
        if self._main_loop is not None:
            self._main_loop.quit()
            self._main_loop = None
        self._bus = None

    def __chooser_response_cb(self, chooser_id, object_id):
        if chooser_id != self._chooser_id:
            return
        logging.debug('ObjectChooser.__chooser_response_cb: %r', object_id)
        self._response_code = Gtk.ResponseType.ACCEPT
        self._object_id = object_id
        self._cleanup()

    def __chooser_cancelled_cb(self, chooser_id):
        if chooser_id != self._chooser_id:
            return
        logging.debug('ObjectChooser.__chooser_cancelled_cb: %r', chooser_id)
        self._response_code = Gtk.ResponseType.CANCEL
        self._cleanup()

    def __name_owner_changed_cb(self, name, old, new):
        logging.debug('ObjectChooser.__name_owner_changed_cb')
        # Journal service disappeared from the bus
        self._response_code = Gtk.ResponseType.CANCEL
        self._cleanup()

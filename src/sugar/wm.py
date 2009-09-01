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

"""
UNSTABLE. Used only internally by Activity and jarabe.
"""

import gtk
import logging

def _property_get_trapped(window, prop, prop_type):
    gtk.gdk.error_trap_push()

    prop_info = window.property_get(prop, prop_type)

    # We just log a message
    error = gtk.gdk.error_trap_pop()
    if error:
        logging.debug('Received X Error (%i) while getting '
                      'a property on a window' % error)

    return prop_info

def _property_change_trapped(window, prop, prop_type, format, mode, data):
    gtk.gdk.error_trap_push()

    window.property_change(prop, prop_type, format, mode, data)

    error = gtk.gdk.error_trap_pop()
    if error:
        logging.debug('Received X Error (%i) while setting '
                      'a property on a window' % error)
        raise RuntimeError('Received X Error (%i) while setting '
                           'a property on a window' % error)
    

def get_activity_id(wnck_window):
    window = gtk.gdk.window_foreign_new(wnck_window.get_xid())
    prop_info = _property_get_trapped(window, '_SUGAR_ACTIVITY_ID', 'STRING')
    if prop_info is None:
        return None
    else:
        return prop_info[2]


def get_bundle_id(wnck_window):
    window = gtk.gdk.window_foreign_new(wnck_window.get_xid())
    prop_info = _property_get_trapped(window, '_SUGAR_BUNDLE_ID', 'STRING')
    if prop_info is None:
        return None
    else:
        return prop_info[2]


def get_sugar_window_type(wnck_window):
    window = gtk.gdk.window_foreign_new(wnck_window.get_xid())
    prop_info = _property_get_trapped(window, '_SUGAR_WINDOW_TYPE', 'STRING')
    if prop_info is None:
        return None
    else:
        return prop_info[2]


def set_activity_id(window, activity_id):
    _property_change_trapped(window, '_SUGAR_ACTIVITY_ID', 'STRING', 8,
                             gtk.gdk.PROP_MODE_REPLACE, activity_id)


def set_bundle_id(window, bundle_id):
    _property_change_trapped(window, '_SUGAR_BUNDLE_ID', 'STRING', 8,
                             gtk.gdk.PROP_MODE_REPLACE, bundle_id)


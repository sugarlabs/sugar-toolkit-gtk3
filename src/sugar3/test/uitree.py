# Copyright (C) 2012, Daniel Narvaez
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
UNSTABLE.
"""

import logging
import time
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Atspi
from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import GObject

key_name_aliases = {
    'enter': 'Return',
    'esc': 'Escape',
    'alt': 'Alt_L',
    'control': 'Control_L',
    'ctrl': 'Control_L',
    'shift': 'Shift_L',
    'del': 'Delete',
    'ins': 'Insert',
    'pageup': 'Page_Up',
    'pagedown': 'Page_Down',
    ' ': 'space',
    '\t': 'Tab',
    '\n': 'Return'
}


def get_root():
    return Node(Atspi.get_desktop(0))


def _retry_find(func):
    def wrapped(*args, **kwargs):
        result = None
        n_retries = 1

        while n_retries <= 50:
            logging.info("Try %d, name=%s role_name=%s" %
                         (n_retries,
                          kwargs.get("name", None),
                          kwargs.get("role_name", None)))

            try:
                result = func(*args, **kwargs)
            except GLib.GError, e:
                # The application is not responding, try again
                if e.code == Atspi.Error.IPC:
                    continue

                logging.error("GError code %d" % e.code)
                raise

            expect_none = kwargs.get("expect_none", False)
            if (not expect_none and result) or \
               (expect_none and not result):
                return result

            time.sleep(1)
            n_retries = n_retries + 1

        return result

    return wrapped


def type_text(string):
    if isinstance(string, unicode):
            string = string.decode('utf-8')
    for char in string:
            key_press(char)


def key_press(key_name):
    key_sym = name_to_sym(key_name)
    Atspi.generate_keyboard_event(key_sym,
                                  None,
                                  Atspi.KeySynthType.SYM)


def uniChar_to_keySym(uniChar):
    if not isinstance(uniChar, unicode):
        uniChar = unicode(uniChar, 'utf-8')
    i = ord(uniChar)
    keySym = Gdk.unicode_to_keyval(i)
    return keySym


def name_to_sym(key_name):
    key_name = key_name_aliases.get(key_name.lower(), key_name)
    key_sym = Gdk.keyval_from_name(key_name)
    if key_sym == 0xffffff or key_sym == 0x0 or key_sym is None:
        try:
            key_sym = uniChar_to_keySym(key_name)
        except:  # not even valid utf-8 char
            try:  # Last attempt run at a keyName ('Meta_L', 'Dash' ...)
                key_sym = getattr(Gdk, 'KEY_' + key_name)
            except AttributeError:
                raise KeyError(key_name)
    return key_sym


def press(button=1, x_offset=0, y_offset=0):
    Atspi.generate_mouse_event(x_offset, y_offset, "b%sp" % button)
    return True


def release(button=1, x_offset=0, y_offset=0):
    Atspi.generate_mouse_event(x_offset, y_offset, "b%sr" % button)
    return True


def absMotion(x_offset=0, y_offset=0):
    Atspi.generate_mouse_event(x_offset, y_offset, "abs")
    return True


def drag(x1, y1, x2, y2):
    GObject.timeout_add(500, press(1, x1, y1))
    GObject.timeout_add(500, absMotion(x2, y2))
    GObject.timeout_add(500, release(1, x2, y2))


class Node:
    def __init__(self, accessible):
        self._accessible = accessible

    def dump(self):
        lines = []
        self._crawl_accessible(self, 0, lines)
        return "\n".join(lines)

    def do_action(self, name):
        for i in range(self._accessible.get_n_actions()):
            # New, incompatible API
            if hasattr(self._accessible, "get_action_name"):
                action_name = self._accessible.get_action_name(i)
            else:
                action_name = Atspi.Action.get_name(self._accessible, i)

            if action_name == name:
                self._accessible.do_action(i)

    def click(self, button=1, x_offset=0, y_offset=0):
        point = self._accessible.get_position(Atspi.CoordType.SCREEN)
        Atspi.generate_mouse_event(point.x+x_offset,
                                   point.y+y_offset,
                                   "b%sc" % button)

    @property
    def name(self):
        return self._accessible.get_name()

    @property
    def role_name(self):
        return self._accessible.get_role_name()

    @property
    def text(self):
        return Atspi.Text.get_text(self._accessible, 0, -1)

    def get_children(self):
        children = []

        for i in range(self._accessible.get_child_count()):
            child = self._accessible.get_child_at_index(i)

            # We sometimes get none children from atspi
            if child is not None:
                children.append(Node(child))

        return children

    @_retry_find
    def find_children(self, name=None, role_name=None):
        def predicate(node):
            return self._predicate(node, name, role_name)

        descendants = []
        self._find_all_descendants(self, predicate, descendants)
        if not descendants:
            return []

        return descendants

    @_retry_find
    def find_child(self, name=None, role_name=None, expect_none=False):
        def predicate(node):
            return self._predicate(node, name, role_name)

        node = self._find_descendant(self, predicate)
        if node is None:
            return None

        return node

    def __str__(self):
        return "[%s | %s]" % (self.name, self.role_name)

    def _predicate(self, node, name, role_name):
        if name is not None and name != node.name:
            return False

        if role_name is not None and role_name != node.role_name:
            return False

        return True

    def _find_descendant(self, node, predicate):
        if predicate(node):
            return node

        for child in node.get_children():
            descendant = self._find_descendant(child, predicate)
            if descendant is not None:
                return descendant

        return None

    def _find_all_descendants(self, node, predicate, matches):
        if predicate(node):
            matches.append(node)

        for child in node.get_children():
            self._find_all_descendants(child, predicate, matches)

    def _crawl_accessible(self, node, depth, lines):
        lines.append("  " * depth + str(node))

        for child in node.get_children():
            self._crawl_accessible(child, depth + 1, lines)

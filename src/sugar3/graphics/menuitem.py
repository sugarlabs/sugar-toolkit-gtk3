# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
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

from sugar3.graphics.icon import Icon
from sugar3.graphics import style


class MenuItem(Gtk.ImageMenuItem):

    def __init__(self, text_label=None, icon_name=None,
                 text_maxlen=style.MENU_WIDTH_CHARS, xo_color=None,
                 file_name=None):
        GObject.GObject.__init__(self)
        self._accelerator = None

        label = Gtk.AccelLabel(label=text_label)
        label.set_alignment(0.0, 0.5)
        label.set_accel_widget(self)
        if text_maxlen > 0:
            label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
            label.set_max_width_chars(text_maxlen)
        self.add(label)
        label.show()

        if icon_name is not None:
            icon = Icon(icon_name=icon_name,
                        pixel_size=style.SMALL_ICON_SIZE)
            if xo_color is not None:
                icon.props.xo_color = xo_color
            self.set_image(icon)
            icon.show()

        elif file_name is not None:
            icon = Icon(file=file_name, pixel_size=style.SMALL_ICON_SIZE)
            if xo_color is not None:
                icon.props.xo_color = xo_color
            self.set_image(icon)
            icon.show()

        self.connect('can-activate-accel', self.__can_activate_accel_cb)
        self.connect('hierarchy-changed', self.__hierarchy_changed_cb)

    def __hierarchy_changed_cb(self, widget, previous_toplevel):
        self._add_accelerator()

    def __can_activate_accel_cb(self, widget, signal_id):
        # Accept activation via accelerators regardless of this widget's state
        return True

    def _add_accelerator(self):
        if self._accelerator is None or self.get_toplevel() is None:
            return

        # TODO: should we remove the accelerator from the prev top level?

        if not hasattr(self.get_toplevel(), 'sugar_accel_group'):
            logging.debug('No Gtk.AccelGroup in the top level window.')
            return

        accel_group = self.get_toplevel().sugar_accel_group
        keyval, mask = Gtk.accelerator_parse(self._accelerator)
        self.add_accelerator('activate', accel_group, keyval, mask,
                             Gtk.AccelFlags.LOCKED | Gtk.AccelFlags.VISIBLE)

    def set_accelerator(self, accelerator):
        self._accelerator = accelerator
        self._add_accelerator()

    def get_accelerator(self):
        return self._accelerator

    accelerator = GObject.Property(type=str, setter=set_accelerator,
                                   getter=get_accelerator)

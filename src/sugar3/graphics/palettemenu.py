# Copyright 2012 One Laptop Per Child
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

import logging

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from sugar3.graphics.icon import Icon
from sugar3.graphics import style


class PaletteMenuBox(Gtk.VBox):
    def __init__(self):
        Gtk.VBox.__init__(self)

    def append_item(self, item_or_widget, horizontal_padding=None,
                    vertical_padding=None):
        item = None
        if (isinstance(item_or_widget, PaletteMenuItem) or
            isinstance(item_or_widget, PaletteMenuItemSeparator)):
            item = item_or_widget
        else:
            item = self._wrap_widget(item_or_widget, horizontal_padding,
                                     vertical_padding)

        self.pack_start(item, False, False, 0)

    def _wrap_widget(self, widget, horizontal_padding, vertical_padding):
        vbox = Gtk.VBox()
        vbox.show()

        if horizontal_padding is None:
            horizontal_padding = style.DEFAULT_SPACING

        if vertical_padding is None:
            vertical_padding = style.DEFAULT_SPACING

        hbox = Gtk.HBox()
        vbox.pack_start(hbox, True, True, vertical_padding)
        hbox.show()

        hbox.pack_start(widget, True, True, horizontal_padding)
        return vbox


class PaletteMenuItemSeparator(Gtk.EventBox):
    """Contains a HSeparator and has the proper height for the menu."""

    __gtype_name__ = 'SugarPaletteMenuItemSeparator'

    def __init__(self):
        Gtk.EventBox.__init__(self)
        separator = Gtk.HSeparator()
        self.add(separator)
        separator.show()
        self.set_size_request(-1, style.DEFAULT_SPACING * 2)


class PaletteMenuItem(Gtk.EventBox):

    __gtype_name__ = 'SugarPaletteMenuItem'

    __gsignals__ = {
        'activate': (GObject.SignalFlags.RUN_FIRST, None, [])
    }

    def __init__(self, text_label=None, icon_name=None, text_maxlen=60,
                 xo_color=None, file_name=None):

        Gtk.EventBox.__init__(self)
        self.set_above_child(True)

        self.icon = None
        self._hbox = Gtk.HBox()

        vbox = Gtk.VBox()
        self.add(vbox)
        vbox.show()

        hbox = Gtk.HBox()
        vbox.pack_start(hbox, True, True, style.DEFAULT_PADDING)
        hbox.show()

        hbox.pack_start(self._hbox, True, True, style.DEFAULT_PADDING)

        if icon_name is not None:
            self.icon = Icon(icon_name=icon_name,
                        icon_size=Gtk.IconSize.SMALL_TOOLBAR)
            if xo_color is not None:
                self.icon.props.xo_color = xo_color
            self._hbox.pack_start(self.icon, expand=False, fill=False,
                                  padding=style.DEFAULT_PADDING)
        elif file_name is not None:
            self.icon = Icon(file=file_name,
                             icon_size=Gtk.IconSize.SMALL_TOOLBAR)
            if xo_color is not None:
                self.icon.props.xo_color = xo_color
            self._hbox.pack_start(self.icon, expand=False, fill=False,
                                  padding=style.DEFAULT_PADDING)

        align = Gtk.Alignment(xalign=0.0, yalign=0.5, xscale=0.0, yscale=0.0)
        self.label = Gtk.Label(text_label)
        if text_maxlen > 0:
            self.label.set_max_width_chars(text_maxlen)
            self.label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        align.add(self.label)
        self._hbox.pack_start(align, expand=True, fill=True,
                        padding=style.DEFAULT_PADDING)

        self.id_bt_release_cb = self.connect('button-release-event',
                self.__button_release_cb)
        self.id_enter_notify_cb = self.connect('enter-notify-event',
                                               self.__enter_notify_cb)
        self.id_leave_notify_cb = self.connect('leave-notify-event',
                                               self.__leave_notify_cb)

        self.show_all()

    def __button_release_cb(self, widget, event):
        self.emit('activate')

    def __enter_notify_cb(self, widget, event):
        self.modify_bg(Gtk.StateType.NORMAL,
                       style.COLOR_BUTTON_GREY.get_gdk_color())

    def __leave_notify_cb(self, widget, event):
        self.modify_bg(Gtk.StateType.NORMAL,
                       style.COLOR_BLACK.get_gdk_color())

    def set_label(self, text_label):
        text = '<span foreground="%s">' % style.COLOR_WHITE.get_html() + \
                    text_label + '</span>'
        self.label.set_markup(text)

    def set_image(self, icon):
        self._hbox.pack_start(icon, expand=False, fill=False,
                              padding=style.DEFAULT_PADDING)
        self._hbox.reorder_child(icon, 0)

    def set_sensitive(self, sensitive):
        is_sensitive = bool(not self.get_state_flags() & \
                                Gtk.StateFlags.INSENSITIVE)
        if is_sensitive == sensitive:
            return

        if sensitive:
            self.handler_unblock(self.id_bt_release_cb)
            self.handler_unblock(self.id_enter_notify_cb)
            self.handler_unblock(self.id_leave_notify_cb)
            self.unset_state_flags(Gtk.StateFlags.INSENSITIVE)
        else:
            self.handler_block(self.id_bt_release_cb)
            self.handler_block(self.id_enter_notify_cb)
            self.handler_block(self.id_leave_notify_cb)
            self.set_state_flags(self.get_state_flags() | \
                                     Gtk.StateFlags.INSENSITIVE,
                                 clear=True)

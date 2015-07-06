# Copyright (C) 2015 Sam Parkinson
# Based off jarabe.view.viewhelp
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

from gettext import gettext as _
import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.toolbutton import ToolButton
from jarabe.model import shell


class Modal(Gtk.Window):

    cancel_clicked_signal = GObject.Signal('cancel-clicked')

    def __init__(self):
        '''
        Create a new modal popup
        '''
        Gtk.Window.__init__(self)
        self._box = Gtk.Box()
        self._box.set_orientation(Gtk.Orientation.VERTICAL)
        self.add(self._box)
        self._box.show()

        self._content_widget = None

        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_border_width(style.LINE_WIDTH)
        self.set_has_resize_grip(False)

        width = min(style.GRID_CELL_SIZE * 8,
                    Gdk.Screen.width() - style.GRID_CELL_SIZE * 2)
        height = min(style.GRID_CELL_SIZE * 12,
                     Gdk.Screen.height() - style.GRID_CELL_SIZE * 2)
        self.set_size_request(width, height)

        self.connect('realize', self.__realize_cb)
        self.connect('hide', self.__hide_cb)
        self.connect('key-press-event', self.__key_press_event_cb)

        toolbar = self.create_toolbar()
        self._box.pack_start(toolbar, False, False, 0)
        toolbar.show()

    def create_toolbar(self):
        toolbar = Gtk.Toolbar()
        toolbar.props.vexpand = False

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_size_request(style.DEFAULT_SPACING, -1)
        toolbar.insert(separator, -1)
        separator.show()

        self._title_label = Gtk.Label()
        self._title_label.set_alignment(0, 0.5)
        tool_item = Gtk.ToolItem()
        tool_item.add(self._title_label)
        self._title_label.show()
        toolbar.insert(tool_item, -1)
        tool_item.show()

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar.insert(separator, -1)
        separator.show()

        cancel = ToolButton(icon_name='dialog-cancel')
        cancel.set_tooltip(_('Cancel'))
        cancel.connect('clicked', self.__cancel_clicked_cb)
        toolbar.insert(cancel, -1)
        cancel.show()

        return toolbar

    @GObject.Property(
        type=str, blurb='Markup for the label at the top of the window')
    def title(self):
        return self._title_label.get_label().lstrip('<b>').rstrip('</b>')

    @title.setter
    def title(self, title):
        self._title_label.set_markup('<b>%s</b>' % title)

    def set_content(self, widget):
        '''
        Set the main modal widget, removing any other
        main widget if one was placed there before
        '''
        if self._content_widget is not None:
            self._box.remove(self._content_widget)
        self._box.pack_start(widget, True, True, 0)
        widget.show()
        self._content_widget = widget

    def __realize_cb(self, widget):
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        window = self.get_window()
        window.set_accept_focus(True)
        shell.get_model().push_modal()

    def __hide_cb(self, widget):
        shell.get_model().pop_modal()

    def __key_press_event_cb(self, window, event):
        if event.keyval == Gdk.KEY_Escape:
            self.__cancel_clicked_cb(None)

    def __cancel_clicked_cb(self, widget):
        self.cancel_clicked_signal.emit()
        self.destroy()


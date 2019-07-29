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

import logging

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

from sugar3.graphics import style
from sugar3.graphics.icon import _SVGLoader

ICON_ENTRY_PRIMARY = Gtk.EntryIconPosition.PRIMARY
ICON_ENTRY_SECONDARY = Gtk.EntryIconPosition.SECONDARY


class IconEntry(Gtk.Entry):

    def __init__(self):
        GObject.GObject.__init__(self)

        self._clear_icon = None
        self._clear_shown = False

        self.connect('key-press-event', self._keypress_event_cb)

    def set_icon_from_name(self, position, name):
        icon_theme = Gtk.IconTheme.get_default()
        icon_info = icon_theme.lookup_icon(name,
                                           Gtk.IconSize.SMALL_TOOLBAR,
                                           0)
        if not icon_info:
            logging.warning('IconEntry set_icon_from_name: icon \'%s\' not '
                            'found in the theme.', name)
            return

        if icon_info.get_filename().endswith('.svg'):
            loader = _SVGLoader()
            entities = {'fill_color': style.COLOR_TOOLBAR_GREY.get_svg(),
                        'stroke_color': style.COLOR_TOOLBAR_GREY.get_svg()}
            handle = loader.load(icon_info.get_filename(), entities, None)
            pixbuf = handle.get_pixbuf()
        else:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_info.get_filename())
        del icon_info
        self.set_icon(position, pixbuf)

    def set_icon(self, position, pixbuf):
        if not isinstance(pixbuf, GdkPixbuf.Pixbuf):
            raise ValueError('Argument must be a pixbuf, not %r.' % pixbuf)
        self.set_icon_from_pixbuf(position, pixbuf)

    def remove_icon(self, position):
        self.set_icon_from_pixbuf(position, None)

    def add_clear_button(self):
        if self.props.text != "":
            self.show_clear_button()
        else:
            self.hide_clear_button()

        self.connect('icon-press', self._icon_pressed_cb)
        self.connect('changed', self._changed_cb)

    def show_clear_button(self):
        if not self._clear_shown:
            self.set_icon_from_name(ICON_ENTRY_SECONDARY,
                                    'entry-cancel')
            self._clear_shown = True

    def hide_clear_button(self):
        if self._clear_shown:
            self.remove_icon(ICON_ENTRY_SECONDARY)
            self._clear_shown = False

    def _keypress_event_cb(self, widget, event):
        keyval = Gdk.keyval_name(event.keyval)
        if keyval == 'Escape':
            self.props.text = ''
            return True
        return False

    def _icon_pressed_cb(self, entru, icon_pos, button):
        if icon_pos == ICON_ENTRY_SECONDARY:
            self.set_text('')
            self.hide_clear_button()

    def _changed_cb(self, icon_entry):
        if not self.props.text:
            self.hide_clear_button()
        else:
            self.show_clear_button()

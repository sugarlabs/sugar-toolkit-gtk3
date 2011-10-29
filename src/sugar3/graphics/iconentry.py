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

import gtk

from sugar.graphics import style
from sugar.graphics.icon import _SVGLoader

ICON_ENTRY_PRIMARY = gtk.ENTRY_ICON_PRIMARY
ICON_ENTRY_SECONDARY = gtk.ENTRY_ICON_SECONDARY


class IconEntry(gtk.Entry):

    def __init__(self):
        gtk.Entry.__init__(self)

        self._clear_icon = None
        self._clear_shown = False

        self.connect('key_press_event', self._keypress_event_cb)

    def set_icon_from_name(self, position, name):
        icon_theme = gtk.icon_theme_get_default()
        icon_info = icon_theme.lookup_icon(name,
                                           gtk.ICON_SIZE_SMALL_TOOLBAR,
                                           0)

        if icon_info.get_filename().endswith('.svg'):
            loader = _SVGLoader()
            entities = {'fill_color': style.COLOR_TOOLBAR_GREY.get_svg(),
                        'stroke_color': style.COLOR_TOOLBAR_GREY.get_svg()}
            handle = loader.load(icon_info.get_filename(), entities, None)
            pixbuf = handle.get_pixbuf()
        else:
            pixbuf = gtk.gdk.pixbuf_new_from_file(icon_info.get_filename())
        del icon_info
        self.set_icon(position, pixbuf)

    def set_icon(self, position, pixbuf):
        if type(pixbuf) is not gtk.gdk.Pixbuf:
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
                                    'dialog-cancel')
            self._clear_shown = True

    def hide_clear_button(self):
        if self._clear_shown:
            self.remove_icon(ICON_ENTRY_SECONDARY)
            self._clear_shown = False

    def _keypress_event_cb(self, widget, event):
        keyval = gtk.gdk.keyval_name(event.keyval)
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

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

from gi.repository import GObject
from gi.repository import Gtk


class ComboBox(Gtk.ComboBox):

    __gtype_name__ = 'SugarComboBox'

    def __init__(self):
        GObject.GObject.__init__(self)

        self._text_renderer = None
        self._icon_renderer = None

        self._model = Gtk.ListStore(GObject.TYPE_PYOBJECT,
                                    GObject.TYPE_STRING,
                                    GdkPixbuf.Pixbuf,
                                    GObject.TYPE_BOOLEAN)
        self.set_model(self._model)

        self.set_row_separator_func(self._is_separator, None)

    def get_value(self):
        """
        Parameters
        ----------
        None :

        Returns:
        --------
        value :

        """
        row = self.get_active_item()
        if not row:
            return None
        return row[0]

    value = GObject.property(
        type=object, getter=get_value, setter=None)

    def _get_real_name_from_theme(self, name, size):
        icon_theme = Gtk.IconTheme.get_default()
        valid_, width, height = Gtk.icon_size_lookup(size)
        info = icon_theme.lookup_icon(name, max(width, height), 0)
        if not info:
            raise ValueError('Icon %r not found.' % name)
        fname = info.get_filename()
        del info
        return fname

    def append_item(self, action_id, text, icon_name=None, file_name=None):
        """
        Parameters
        ----------
        action_id :

        text :

        icon_name=None :

        file_name=None :

        Returns
        -------
        None

        """
        if not self._icon_renderer and (icon_name or file_name):
            self._icon_renderer = Gtk.CellRendererPixbuf()

            settings = self.get_settings()
            valid_, w, h = Gtk.icon_size_lookup_for_settings(
                settings, Gtk.IconSize.MENU)
            self._icon_renderer.props.stock_size = max(w, h)

            self.pack_start(self._icon_renderer, False)
            self.add_attribute(self._icon_renderer, 'pixbuf', 2)

        if not self._text_renderer and text:
            self._text_renderer = Gtk.CellRendererText()
            self.pack_end(self._text_renderer, True)
            self.add_attribute(self._text_renderer, 'text', 1)

        if icon_name or file_name:
            if text:
                size = Gtk.IconSize.MENU
            else:
                size = Gtk.IconSize.LARGE_TOOLBAR
            valid_, width, height = Gtk.icon_size_lookup(size)

            if icon_name:
                file_name = self._get_real_name_from_theme(icon_name, size)

            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                                                file_name, width, height)
        else:
            pixbuf = None

        self._model.append([action_id, text, pixbuf, False])

    def append_separator(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        None

        """
        self._model.append([0, None, None, True])

    def get_active_item(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        Active_item :

        """
        index = self.get_active()
        if index == -1:
            index = 0

        row = self._model.iter_nth_child(None, index)
        if not row:
            return None
        return self._model[row]

    def remove_all(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        None

        """
        self._model.clear()

    def _is_separator(self, model, row, data):
        return model[row][3]

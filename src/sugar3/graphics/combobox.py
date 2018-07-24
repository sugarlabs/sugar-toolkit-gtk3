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

'''
The combobox module provides a combo box; a button like widget which
creates a list popup when clicked.  It's best used outside of a
toolbar when the user needs to choose from a *short* list of items.

Example:

.. literalinclude:: ../examples/combobox.py
'''

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import GdkPixbuf


class ComboBox(Gtk.ComboBox):
    '''
    This class provides a simple wrapper based on the :class:`Gtk.ComboBox`.
    This lets you make a list of items, with a value, label and optionally an
    icon.
    '''
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
        '''
        The value of the currently selected item; the same as the `value`
        argument that was passed to the `append_item` func.

        Returns:
            object, value of selected item
        '''
        row = self.get_active_item()
        if not row:
            return None
        return row[0]

    value = GObject.Property(
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

    def append_item(self, value, text, icon_name=None, file_name=None):
        '''
        This function adds another item to the bottom of the combo box list.

        If either `icon_name` or `file_name` are supplied and icon column
        will be added to the combo box list.

        Args:
            value (object):  the value that will be returned by `get_value`,
                when this item is selected
            text (str):  the user visible label for the item
            icon_name (str):  the name of the icon in the theme to use for
                this item, optional and conflicting with `file_name`
            file_name (str):  the path to a sugar (svg) icon to use for this
                item, optional and conflicting with `icon_name`
        '''
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

        self._model.append([value, text, pixbuf, False])

    def append_separator(self):
        '''
        Add a separator to the bottom of the combo box list.  The separator
        can not be selected.
        '''
        self._model.append([0, None, None, True])

    def get_active_item(self):
        '''
        Get the row of data for the currently selected item.

        Returns:
            row of data in the format::

                [value, text, pixbuf, is_separator]
        '''
        index = self.get_active()
        if index == -1:
            index = 0

        row = self._model.iter_nth_child(None, index)
        if not row:
            return None
        return self._model[row]

    def remove_all(self):
        '''
        Remove all list items from the combo box.
        '''
        self._model.clear()

    def _is_separator(self, model, row, data):
        return model[row][3]

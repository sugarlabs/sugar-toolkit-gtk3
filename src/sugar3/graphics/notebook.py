# Copyright (C) 2007, Eduardo Silva (edsiper@gmail.com)
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
Notebook class

This class creates a :class:`Gtk.Notebook` widget supporting
a close button in every tab when the `can-close-tabs` gproperty
is enabled (True).

.. literalinclude:: ../examples/notebook.py
'''

from gi.repository import Gtk
from gi.repository import GObject


if not hasattr(GObject.ParamFlags, 'READWRITE'):
    GObject.ParamFlags.READWRITE = GObject.ParamFlags.WRITABLE | \
        GObject.ParamFlags.READABLE


class Notebook(Gtk.Notebook):
    '''
    Notebook class that creates a :class:`Gtk.Notebook`. It is possible to set
    the `can-close-tabs` property from the constructor
    through Notebook(can_close_tabs=True)
    '''
    __gtype_name__ = 'SugarNotebook'

    __gproperties__ = {
        'can-close-tabs': (bool, None, None, False,
                           GObject.ParamFlags.READWRITE |
                           GObject.ParamFlags.CONSTRUCT_ONLY),
    }

    def __init__(self, **kwargs):
        # Initialise the Widget

        #    Side effects:
        #        Set the 'can-close-tabs' property using **kwargs
        #        Set True the scrollable notebook property

        self._can_close_tabs = None
        GObject.GObject.__init__(self, **kwargs)

        self.set_scrollable(True)
        self.set_visible(True)

    def do_set_property(self, pspec, value):
        '''
        Implementation method. Use notebook.props to set properties.
        '''
        if pspec.name == 'can-close-tabs':
            self._can_close_tabs = value
        else:
            raise AssertionError

    def _add_icon_to_button(self, button):
        icon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        image = Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.MENU)
        Gtk.Button.set_relief(button, Gtk.ReliefStyle.NONE)

        settings = Gtk.Widget.get_settings(button)
        valid_, w, h = Gtk.icon_size_lookup_for_settings(settings,
                                                         Gtk.IconSize.MENU)
        Gtk.Widget.set_size_request(button, w + 4, h + 4)
        image.set_visible(True)
        icon_box.append(image)
        button.set_child(icon_box)
        icon_box.set_visible(True)

    def _create_custom_tab(self, text, child):
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        tab_label = Gtk.Label(label=text)

        tab_button = Gtk.Button()
        tab_button.connect('clicked', self._close_page, child)

        # Add a picture on a button
        self._add_icon_to_button(tab_button)

        tab_label.set_visible(True)
        tab_button.set_visible(True)

        tab_box.append(tab_label)
        tab_box.append(tab_button)

        tab_box.set_visible(True)

        return tab_box

    def add_page(self, text_label, widget):
        '''
        Adds a page to the notebook and sets the newly added page as current.
        Returns True if the page is successfully added to the notebook.
        If `can-close-tabs` is true, then a GtkEventBox is also created
        to close the tab.

        Args:
            text_label (string): label of page to be added

            widget (Gtk.Widget): widget to be used as contents of current page
        '''
        # Add a new page to the notebook
        if self._can_close_tabs:
            tab_box = self._create_custom_tab(text_label, widget)
            self.append_page(widget, tab_box)
        else:
            self.append_page(widget, Gtk.Label(label=text_label))

        pages = self.get_n_pages()

        # Set the new page
        self.set_current_page(pages - 1)
        self.set_visible(True)

        return True

    def _close_page(self, button, child):
        # Remove a page from the notebook
        page = self.page_num(child)

        if page != -1:
            self.remove_page(page)

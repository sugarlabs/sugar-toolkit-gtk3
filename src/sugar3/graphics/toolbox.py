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

'''
A toolbox holds a group of toolbars in a list. One toolbar is displayed
at a time. Toolbars are assigned an index and can be accessed using this index.
Indices are generated in the order the toolbars are added.
'''

from gi.repository import Gtk
from gi.repository import GObject

from sugar3.graphics import style


class Toolbox(Gtk.VBox):
    '''
    Class to represent the toolbox of an activity. Groups a
    number of toolbars vertically, which can be accessed using their
    indices. The current toolbar is the only one displayed.

    Emits `current-toolbar-changed` signal when the
    current toolbar is changed. This signal takes the current page index
    as an argument.
    '''

    __gtype_name__ = 'SugarToolbox'

    __gsignals__ = {
        'current-toolbar-changed': (GObject.SignalFlags.RUN_FIRST,
                                    None, ([int])),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self._notebook = Gtk.Notebook()
        self._notebook.set_tab_pos(Gtk.PositionType.BOTTOM)
        self._notebook.set_show_border(False)
        self._notebook.set_show_tabs(False)
        self._notebook.props.tab_vborder = style.TOOLBOX_TAB_VBORDER
        self._notebook.props.tab_hborder = style.TOOLBOX_TAB_HBORDER
        self.pack_start(self._notebook, True, True, 0)
        self._notebook.show()

        self._separator = Gtk.HSeparator()
        self._separator.modify_bg(Gtk.StateType.NORMAL,
                                  style.COLOR_PANEL_GREY.get_gdk_color())
        self._separator.set_size_request(1, style.TOOLBOX_SEPARATOR_HEIGHT)
        self.pack_start(self._separator, False, False, 0)

        self._notebook.connect('notify::page', self._notify_page_cb)

    def _notify_page_cb(self, notebook, pspec):
        self.emit('current-toolbar-changed', notebook.props.page)

    def add_toolbar(self, name, toolbar):
        '''
        Adds a toolbar to this toolbox. Toolbar will be added
        to the end of this toolbox, and it's index will be
        1 greater than the previously added index (index will be
        0 if it is the first toolbar added).

        Args:
            name (string): name of toolbar to be added

            toolbar (.. :class:`Gtk.Toolbar`):
            Gtk.Toolbar to be appended to this toolbox
        '''
        label = Gtk.Label(label=name)
        req = label.size_request()
        label.set_size_request(max(req.width, style.TOOLBOX_TAB_LABEL_WIDTH),
                               -1)
        label.set_alignment(0.0, 0.5)

        event_box = Gtk.EventBox()

        alignment = Gtk.Alignment(xscale=1.0, yscale=1.0)
        alignment.set_padding(0, 0, style.TOOLBOX_HORIZONTAL_PADDING,
                              style.TOOLBOX_HORIZONTAL_PADDING)

        alignment.add(toolbar)
        event_box.add(alignment)
        alignment.show()
        event_box.show()

        self._notebook.append_page(event_box, label)

        if self._notebook.get_n_pages() > 1:
            self._notebook.set_show_tabs(True)
            self._separator.show()

    def remove_toolbar(self, index):
        '''
        Removes toolbar at the index specified.

        Args:
            index (int): index of the toolbar to be removed
        '''
        self._notebook.remove_page(index)

        if self._notebook.get_n_pages() < 2:
            self._notebook.set_show_tabs(False)
            self._separator.hide()

    def set_current_toolbar(self, index):
        '''
        Sets the current toolbar to that of the index specified and
        displays it.

        Args:
            index (int): index of toolbar to be set as current toolbar
        '''
        self._notebook.set_current_page(index)

    def get_current_toolbar(self):
        '''
        Returns current toolbar.
        '''
        return self._notebook.get_current_page()

    current_toolbar = property(get_current_toolbar, set_current_toolbar)

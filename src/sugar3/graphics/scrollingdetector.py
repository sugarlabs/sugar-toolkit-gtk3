# Copyright (C) 2014, Sugarlabs
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

from gi.repository import GObject
from gi.repository import GLib

from sugar3.graphics.icon import CellRendererIcon


class ScrollingDetector(GObject.GObject):
    """
    """

    scroll_start_signal = GObject.Signal('scroll-start')
    scroll_end_signal = GObject.Signal('scroll-end')

    def __init__(self, scrolled_window, timeout=100):
        self._scrolled_window = scrolled_window
        self._timeout = timeout
        self.is_scrolling = False
        self._prev_value = 0

        self.connect_scrolled_window()
        GObject.GObject.__init__(self)

    def connect_scrolled_window(self):
        adj = self._scrolled_window.get_vadjustment()
        adj.connect('value-changed', self._value_changed_cb)

    def _check_scroll_cb(self, adj):
        if (adj.props.value == self._prev_value):
            self.is_scrolling = False
            self.scroll_end_signal.emit()
            return False

        self._prev_value = adj.props.value
        return True

    def _value_changed_cb(self, adj):
        if (self.is_scrolling):
            return

        self.is_scrolling = True
        self.scroll_start_signal.emit()
        self._prev_value = adj.props.value
        GLib.timeout_add(self._timeout, self._check_scroll_cb, adj)


    def connect_treeview(self, treeview):
        """
        treeview -- Gtk.TreeView: a TreeView with CellRendererIcons already
                    added.
        """
        for column in treeview.get_columns():
            for cell_renderer in column.get_cells():
                if isinstance(cell_renderer, CellRendererIcon):
                    cell_renderer.connect_to_scroller(self)

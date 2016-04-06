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
'''
A module for creating modal popups.

Example:
    Show a label in a modal::

        from gi.repository import Gtk
        from sugar3.graphics.modal import Modal

        m = Modal()
        m.title = 'Modal title'
        m.cancel_clicked_signal.connect(Gtk.main_quit)
        m.show()

        # The Modal class allows custom content
        l = Gtk.Label()
        l.set_text('Hello world')
        m.set_content(l)
        l.show()

        Gtk.main()
'''

from gettext import gettext as _
import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

from sugar3 import profile
from sugar3.graphics import style
from sugar3.graphics.icon import CellRendererIcon
from sugar3.graphics.iconentry import IconEntry, ICON_ENTRY_PRIMARY
from sugar3.graphics.toolbutton import ToolButton
from jarabe.model import shell


class Modal(Gtk.Window):
    '''
    Create a new empty modal popup.  The modal popup will have a
    toolbar with text on the left and a cancel button on the right.

    The `cancel-clicked` signal is emited with the user clicks the
    cancel button on the default toolbar.

    Args:
        title (str): markup for the label at the top of the window

    ..code-block:: python

        from gi.repository import Gtk
        from sugar3.graphics.modal import Modal

        m = Modal()
        m.title = 'Modal title'
        m.cancel_clicked_signal.connect(Gtk.main_quit)
        m.show()

        # The Modal class allows custom content
        l = Gtk.Label()
        l.set_text('Hello world')
        m.set_content(l)
        l.show()

        Gtk.main()
    '''

    cancel_clicked_signal = GObject.Signal('cancel-clicked')

    def __init__(self):
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
        '''
        The create toolbar created the toolbar of a modal and could
        be overridden.  Changing the toolbar may render the `title`
        property and `cancel-clicked` signal broken.

        Returns:
            :class:`Gtk.Toolbar`, toolbar for the modal
        '''
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
        Set the main modal widget, removing any other main widget
        if one was placed there before.

        Args:
            widget (:class:`Gtk.Widget`): the new main widget
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


class SelectorModal(Modal):
    '''
    The SelectorModal is a Modal popup that has a list of items.  It
    supports the user searching or clicking on an item to activate
    it, or selecting the cancel button.  The `model` property is a
    :class:`sugar3.graphics.modal.SelectorModel` which should be
    used to control the contents of the modal.

    The `item-selected` signal is emited when an item is activated
    and contains the `data` object supplied when creating the item.

    ..code-block:: python

        from gi.repository import Gtk
        from sugar3.graphics.modal import SelectorModal

        def item_selected(modal, data):
            print 'Selected:', data
            Gtk.main_quit()

        m = SelectorModal()
        m.title = 'Please select something'
        m.item_selected_signal.connect(item_selected)
        m.cancel_clicked_signal.connect(Gtk.main_quit)
        m.show()

        # Manually setting the data
        m.model.add_item('Item 1', icon_name='computer-xo', data=1)
        m.model.add_item('Item 2', icon_name='computer-xo', data=2)
        # Using the text as data
        m.model.add_item('Item 3', icon_name='computer-xo')
        m.model.add_item('Item 4', icon_name='computer-xo')

        Gtk.main()
    '''

    item_selected_signal = GObject.Signal('item-selected',
                                          arg_types=([object]))

    def __init__(self):
        Modal.__init__(self)
        self.connect('realize', self.__realize_cb)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.modify_bg(Gtk.StateType.NORMAL, style.COLOR_WHITE.get_gdk_color())
        self.set_content(box)
        box.show()

        self._search = IconEntry()
        self._search.placeholder_text = _('Search')
        self._search.add_clear_button()
        self._search.set_icon_from_name(ICON_ENTRY_PRIMARY, 'system-search')
        box.pack_start(self._search, False, False, style.DEFAULT_SPACING)
        self._search.show()
        self._search.grab_focus()

        self.model = SelectorModel()
        self._filter_model = self.model.filter_new()
        self._filter_model.set_visible_func(self.__model_filter_cb)
        self._search.connect('changed', self.__search_change_cb)
        self._search.connect('activate', self.__search_activate_cb)

        self._tree_view = Gtk.TreeView(self._filter_model)
        self._tree_view.props.headers_visible = False
        self._tree_view.props.activate_on_single_click = True
        box.pack_start(self._tree_view, True, True, 0)
        self._tree_view.connect('row-activated', self.__tree_view_activate_cb)
        self._tree_view.show()

        cell_icon = _CellRendererIcon()
        column = Gtk.TreeViewColumn()
        column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        column.props.fixed_width = cell_icon.props.width
        column.pack_start(cell_icon, True)
        column.add_attribute(cell_icon, 'icon-name',
                             SelectorModel.COLUMN_ICON_NAME)
        column.add_attribute(cell_icon, 'file-name',
                             SelectorModel.COLUMN_ICON_FILE)
        column.add_attribute(cell_icon, 'xo-color',
                             SelectorModel.COLUMN_ICON_COLOR)
        self._tree_view.append_column(column)

        cell_text = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn()
        column.pack_start(cell_text, True)
        column.add_attribute(cell_text, 'text', SelectorModel.COLUMN_TEXT)
        self._tree_view.append_column(column)

    def __realize_cb(self, widget):
        self._tree_view.set_cursor(Gtk.TreePath.new_first())

    def __model_filter_cb(self, model, row, data):
        query = self._search.get_text().lower()
        text = self.model.get_value(row, SelectorModel.COLUMN_TEXT).lower()
        return query in text

    def __search_change_cb(self, entry):
        self._filter_model.refilter()
        # Make sure the top entry is highlighted
        self._tree_view.set_cursor(Gtk.TreePath.new_first())

    def __search_activate_cb(self, entry):
        row = self._filter_model.get_iter(Gtk.TreePath.new_first())
        if row is not None:
            data = self._filter_model.get_value(
                row, SelectorModel.COLUMN_DATA)
            self.item_selected_signal.emit(data)
            self.destroy()

    def __tree_view_activate_cb(self, tree_view, path, column):
        row = self._filter_model.get_iter(path)
        data = self._filter_model.get_value(row, SelectorModel.COLUMN_DATA)
        self.item_selected_signal.emit(data)
        self.destroy()


class SelectorModel(Gtk.ListStore):
    '''
    The SelectorModel is used to provide data to a
    :class:`sugar3.graphics.modal.SelectorModal` and should not
    be created directly.
    '''

    COLUMN_ICON_NAME = 0
    COLUMN_ICON_FILE = 1
    COLUMN_ICON_COLOR = 2
    COLUMN_TEXT = 3
    COLUMN_DATA = 4

    COLUMN_TYPES = [str, str, object, str, object]

    def __init__(self):
        Gtk.ListStore.__init__(self, *self.COLUMN_TYPES)

    def add_item(self, text, icon_name=None, icon_file=None,
                 icon_color=None, data=None):
        '''
        Add an item to the model.

        Args:
            text (str): a text label for the item, shown to the user
            icon_name (str, optional): icon name for the item's icon
            icon_file (str, optional): file path for the item's icon
            icon_color (:class:`sugar3.graphics.xocolor.XoColor`, optional):
                a color for the icon, defaults to the profile color
            data (object, optional): data to be passed to the model's
                `item-selected` signal, defaults to the `text` value

        Raises:
            ValueError is no icon is given
        '''
        if icon_name is None and icon_file is None:
            raise ValueError('Either icon_name or icon_file is required')
        if icon_color is None:
            icon_color = profile.get_color()
        if data is None:
            data = text
        self.append([icon_name, icon_file, icon_color, text, data])


class _CellRendererIcon(CellRendererIcon):
    def __init__(self):
        CellRendererIcon.__init__(self)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE

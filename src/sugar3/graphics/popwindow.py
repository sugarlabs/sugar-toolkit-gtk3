# Copyright (C) 2016 Abhijit Patel
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
Provide a PopWindow class for pop-up windows.
Making PopWindow containing Gtk.Toolbar which also contains Gtk.Label
and Toolbutton at the end of the Gtk.Toolbar.

It is possible to change props like size and add more widgets PopWindow
and also to Gtk.Toolbar.

Example:
    .. literalinclude: ..sugar/src/jarabe/view/viewsource.py
    .. literalinclude: ..sugar/src/jarabe/view/viewhelp.py
'''
from gettext import gettext as _
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import GObject

from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton

from jarabe.model import shell


class PopWindow(Gtk.Window):
    """
    UI interface for activity Pop-up Windows.
    PopWindows are the windows that open on the top of the current window.
    These pop-up windows don't cover the whole screen.
    They contain canvas content, alerts messages, a tray and a
    toolbar.

    FULLSCREEN and HALF_WIDTH for setting size of the window.

    Kwargs:
        size (int,int): size to be set of the window
        window_xid (xlib.Window): xid of the parent window
    """
    FULLSCREEN = (Gdk.Screen.width() - style.GRID_CELL_SIZE * 3,
                  Gdk.Screen.height() - style.GRID_CELL_SIZE * 2)

    HALF_WIDTH = ((Gdk.Screen.height() - style.GRID_CELL_SIZE * 3)/2,
                  (Gdk.Screen.height() - style.GRID_CELL_SIZE * 2))

    def __init__(self, window_xid=None, **kwargs):
        Gtk.Window.__init__(self, **kwargs)
        self._parent_window_xid = window_xid

        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_border_width(style.LINE_WIDTH)
        self.set_has_resize_grip(False)
        self.props.size = self.FULLSCREEN

        self.connect('realize', self.__realize_cb)
        self.connect('key-press-event', self.__key_press_event_cb)
        self.connect('hide', self.__hide_cb)

        self._vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self._vbox)
        self._vbox.show()

        self._title_box = TitleBox()
        self._title_box.close_button.connect(
            'clicked',
            self.__close_button_clicked_cb)
        self._title_box.set_size_request(-1, style.GRID_CELL_SIZE)

        self._vbox.pack_start(self._title_box, False, True, 0)
        self._title_box.show()

        # Note:
        # Not displaying the pop-up from here instead allowing
        # the child class to display the window after modifications
        # like chaninging window size, decorating, changing position.

    def set_size(self, size):
        width, height = size
        self.set_size_request(width, height)

    size = GObject.Property(type=None, setter=set_size)

    def get_title_box(self):
        '''
        Getter method for title-box

        Returns:
            self._title_box (): Title or Tool Box
        '''
        return self._title_box

    title_box = GObject.Property(type=str, getter=get_title_box)

    def get_vbox(self):
        '''
        Getter method for canvas

        Returns:
            self._vbox (Gtk.Box): canvas
        '''
        return self._vbox
    vbox = GObject.Property(type=str, getter=get_vbox)

    def __close_button_clicked_cb(self, button):
        self.destroy()

    def __key_press_event_cb(self, window, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == 'Escape':
            self.destroy()

    def __realize_cb(self, widget):
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        window = self.get_window()
        window.set_accept_focus(True)

        if self._parent_window_xid is not None:
            display = Gdk.Display.get_default()
            parent = GdkX11.X11Window.foreign_new_for_display(
                display, self._parent_window_xid)
            window.set_transient_for(parent)
            shell.get_model().push_modal()

    def __hide_cb(self, widget):
        shell.get_model().pop_modal()

    def add_view(self, widget, expand=True, fill=True, padding=0):
        '''
        Adds child to the vbox.

        Args:
            widget (Gtk.Widget): widget to be added

            expand (bool): True if child is to be given extra space allocated
                to vbox.

            fill (bool): True if space given to child by the expand option is
                actually allocated to child, rather than just padding it.

            padding (int): extra space in pixels to put between child and its
                neighbors, over and above the global amount specified
                by spacing in vbox.

        Returns:
            None
        '''
        self._vbox.pack_start(widget, expand, fill, padding)


class TitleBox(Gtk.Toolbar):
    '''
    Title box at the top of the pop-up window.
    Title and close button are added to the box and as needed more widgets
    can be added using self.add_widget method.
    This box is optional as the inherited class can remove this block by
    setting the self._set_title_box to False.
    '''

    def __init__(self):
        Gtk.Toolbar.__init__(self)

        self.close_button = ToolButton(icon_name='dialog-cancel')
        self.close_button.set_tooltip(_('Close'))
        self.insert(self.close_button, -1)
        self.close_button.show()

        self._label = Gtk.Label()
        self._label.set_alignment(0, 0.5)

        tool_item = Gtk.ToolItem()
        tool_item.set_expand(True)
        tool_item.add(self._label)
        self._label.show()
        self.insert(tool_item, 0)
        tool_item.show()

    def set_title(self, title):
        '''
        setter function for 'title' property.
        Args:
           title (str): title for the pop-up window
        '''
        self._label.set_markup('<b>%s</b>' % title)
        self._label.show()

    title = GObject.Property(type=str, setter=set_title)

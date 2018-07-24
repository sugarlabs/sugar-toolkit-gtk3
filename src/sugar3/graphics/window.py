# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2009, Aleksey Lim, Sayamindu Dasgupta
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

import gi
gi.require_version('GdkX11', '3.0')

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import Gtk

from sugar3.graphics.icon import Icon
from sugar3.graphics import palettegroup
from sugar3.graphics import style


_UNFULLSCREEN_BUTTON_VISIBILITY_TIMEOUT = 2


class UnfullscreenButton(Gtk.Window):
    """
    A ready-made "Unfullscreen" button.

    Used by :class:`~sugar3.graphics.window.Window` to exit fullscreen
    mode.
    """

    def __init__(self):
        Gtk.Window.__init__(self)

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        self.set_border_width(0)

        self.props.accept_focus = False

        # Setup estimate of width, height
        valid_, w, h = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
        self._width = w
        self._height = h

        screen = self.get_screen()
        screen.connect('size-changed', self._screen_size_changed_cb)

        self._button = Gtk.Button()
        self._button.set_relief(Gtk.ReliefStyle.NONE)

        self._icon = Icon(icon_name='view-return',
                          pixel_size=style.STANDARD_ICON_SIZE)
        self._icon.show()
        self._button.add(self._icon)

        self._button.show()
        self.add(self._button)

    def connect_button_clicked(self, cb):
        self._button.connect('clicked', cb)

    def _reposition(self):
        x = Gdk.Screen.width() - self._width
        self.move(x, 0)

    def do_get_preferred_width(self):
        minimum, natural = Gtk.Window.do_get_preferred_width(self)
        self._width = minimum
        self._reposition()
        return minimum, natural

    def _screen_size_changed_cb(self, screen):
        self._reposition()


class Window(Gtk.Window):
    """
    An activity window.

    Used as a container to display things that happen in an activity.
    A window must contain a canvas widget, and a toolbar box widget.
    A window may also contain alert message widgets and a tray widget.

    Widgets are kept in a vertical box in this order;
        * toolbar box,
        * alerts,
        * canvas,
        * tray.

    A window may be in fullscreen or non-fullscreen mode.  In fullscreen
    mode, the toolbar and tray are hidden.

    Motion events are tracked, and an unfullscreen button is shown when
    the mouse is moved into the top right corner of the canvas.

    Key press events are tracked;
        * :kbd:`escape` will cancel fullscreen mode,
        * :kbd:`Alt+space` will toggle tray visibility.

    """

    def __init__(self, **args):
        self._enable_fullscreen_mode = True

        GObject.GObject.__init__(self, **args)

        self.set_decorated(False)
        self.maximize()
        self.connect('realize', self.__window_realize_cb)
        self.connect_after('key-press-event', self.__key_press_cb)

        # OSK support: canvas auto panning based on input focus
        if GObject.signal_lookup('request-clear-area', Window) != 0 and \
                GObject.signal_lookup('unset-clear-area', Window) != 0:
            self.connect('size-allocate', self.__size_allocate_cb)
            self.connect('request-clear-area', self.__request_clear_area_cb)
            self.connect('unset-clear-area', self.__unset_clear_area_cb)
            self._clear_area_dy = 0

        self._toolbar_box = None
        self._alerts = []
        self._canvas = None
        self.tray = None

        self.__vbox = Gtk.VBox()
        self.__hbox = Gtk.HBox()
        self.__vbox.pack_start(self.__hbox, True, True, 0)
        self.__hbox.show()

        self.add_events(Gdk.EventMask.POINTER_MOTION_HINT_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.TOUCH_MASK)
        self.connect('motion-notify-event', self.__motion_notify_cb)
        self.connect('button-release-event', self.__button_press_event_cb)

        self.add(self.__vbox)
        self.__vbox.show()

        self._is_fullscreen = False
        self._unfullscreen_button = UnfullscreenButton()
        self._unfullscreen_button.set_transient_for(self)
        self._unfullscreen_button.connect_button_clicked(
            self.__unfullscreen_button_clicked)
        self._unfullscreen_button_timeout_id = None

    def reveal(self):
        """
        Make window active.

        Brings the window to the top and makes it active, even after
        invoking on response to non-GTK events (in contrast to
        present()).  See bug #1423
        """
        window = self.get_window()
        if window is None:
            self.show()
            return
        timestamp = Gtk.get_current_event_time()
        if not timestamp:
            timestamp = GdkX11.x11_get_server_time(window)
        window.focus(timestamp)

    def is_fullscreen(self):
        """
        Check if the window is fullscreen.

        Returns:
            bool: window is fullscreen
        """
        return self._is_fullscreen

    def fullscreen(self):
        """
        Make the window fullscreen.  The toolbar and tray will be
        hidden, and the :class:`UnfullscreenButton` will be shown for
        a short time.
        """
        palettegroup.popdown_all()
        if self._toolbar_box is not None:
            self._toolbar_box.hide()
        if self.tray is not None:
            self.tray.hide()

        self._is_fullscreen = True

        if self.props.enable_fullscreen_mode:
            self._unfullscreen_button.show()

            if self._unfullscreen_button_timeout_id is not None:
                GLib.source_remove(self._unfullscreen_button_timeout_id)
                self._unfullscreen_button_timeout_id = None

            self._unfullscreen_button_timeout_id = \
                GLib.timeout_add_seconds(
                    _UNFULLSCREEN_BUTTON_VISIBILITY_TIMEOUT,
                    self.__unfullscreen_button_timeout_cb)

    def unfullscreen(self):
        """
        Restore the window to non-fullscreen mode.  The
        :class:`UnfullscreenButton` will be hidden, and the toolbar
        and tray will be shown.
        """
        if self._toolbar_box is not None:
            self._toolbar_box.show()
        if self.tray is not None:
            self.tray.show()

        self._is_fullscreen = False

        if self.props.enable_fullscreen_mode:
            self._unfullscreen_button.hide()

            if self._unfullscreen_button_timeout_id:
                GLib.source_remove(self._unfullscreen_button_timeout_id)
                self._unfullscreen_button_timeout_id = None

    def set_canvas(self, canvas):
        """
        Set canvas widget.

        Args:
            canvas (:class:`Gtk.Widget`): the canvas to set
        """
        if self._canvas:
            self.__hbox.remove(self._canvas)

        if canvas:
            self.__hbox.pack_start(canvas, True, True, 0)

        self._canvas = canvas
        self.__vbox.set_focus_child(self._canvas)

    def get_canvas(self):
        """
        Get canvas widget.

        Returns:
            :class:`Gtk.Widget`: the canvas
        """
        return self._canvas

    canvas = property(get_canvas, set_canvas)
    """
    Property: the :class:`Gtk.Widget` to be shown as the canvas, below
    the toolbar and alerts, and above the tray.
    """

    def get_toolbar_box(self):
        """
        Get :class:`~sugar3.graphics.toolbarbox.ToolbarBox` widget.

        Returns:
            :class:`~sugar3.graphics.toolbarbox.ToolbarBox`: the
                current toolbar box of the window
        """
        return self._toolbar_box

    def set_toolbar_box(self, toolbar_box):
        """
        Set :class:`~sugar3.graphics.toolbarbox.ToolbarBox` widget.

        Args:
            toolbar_box (:class:`~sugar3.graphics.toolbarbox.ToolbarBox`):
                the toolbar box to set as current
        """
        if self._toolbar_box:
            self.__vbox.remove(self._toolbar_box)

        if toolbar_box:
            self.__vbox.pack_start(toolbar_box, False, False, 0)
            self.__vbox.reorder_child(toolbar_box, 0)

        self._toolbar_box = toolbar_box

    toolbar_box = property(get_toolbar_box, set_toolbar_box)
    """
    Property: the :class:`~sugar3.graphics.toolbarbox.ToolbarBox` to
    be shown above the alerts and canvas.
    """

    def set_tray(self, tray, position):
        """
        Set the tray.

        Args:
            tray (:class:`~sugar3.graphics.tray.HTray` \
                or :class:`~sugar3.graphics.tray.VTray`): the tray to set
            position (:class:`Gtk.PositionType`): the edge to set the tray at
        """
        if self.tray:
            box = self.tray.get_parent()
            box.remove(self.tray)

        if position == Gtk.PositionType.LEFT:
            self.__hbox.pack_start(tray, False, False, 0)
        elif position == Gtk.PositionType.RIGHT:
            self.__hbox.pack_end(tray, False, False, 0)
        elif position == Gtk.PositionType.BOTTOM:
            self.__vbox.pack_end(tray, False, False, 0)

        self.tray = tray

    def add_alert(self, alert):
        """
        Add an alert to the window.

        You must call :class:`Gtk.Widget`. :func:`show` on the alert
        to make it visible.

        Args:
            alert (:class:`~sugar3.graphics.alert.Alert`): the alert
                to add
        """
        self._alerts.append(alert)
        if len(self._alerts) == 1:
            self.__vbox.pack_start(alert, False, False, 0)
            if self._toolbar_box is not None:
                self.__vbox.reorder_child(alert, 1)
            else:
                self.__vbox.reorder_child(alert, 0)

    def remove_alert(self, alert):
        """
        Remove an alert message from the window.

        Args:
            alert (:class:`~sugar3.graphics.alert.Alert`): the alert
                to remove
        """
        if alert in self._alerts:
            self._alerts.remove(alert)
            # if the alert is the visible one on top of the queue
            if alert.get_parent() is not None:
                self.__vbox.remove(alert)
                if len(self._alerts) >= 1:
                    self.__vbox.pack_start(self._alerts[0], False, False, 0)
                    if self._toolbar_box is not None:
                        self.__vbox.reorder_child(self._alerts[0], 1)
                    else:
                        self.__vbox.reorder_child(self._alert[0], 0)

    def __window_realize_cb(self, window):
        group = Gtk.Window()
        group.realize()
        window.get_window().set_group(group.get_window())

    def __key_press_cb(self, widget, event):
        key = Gdk.keyval_name(event.keyval)
        if event.get_state() & Gdk.ModifierType.MOD1_MASK:
            if self.tray is not None and key == 'space':
                self.tray.props.visible = not self.tray.props.visible
                return True
        elif key == 'Escape' and self._is_fullscreen and \
                self.props.enable_fullscreen_mode:
            self.unfullscreen()
            return True
        return False

    def __unfullscreen_button_clicked(self, button):
        self.unfullscreen()

    def __button_press_event_cb(self, widget, event):
        self._show_unfullscreen_button()
        return False

    def __motion_notify_cb(self, widget, event):
        self._show_unfullscreen_button()
        return False

    def _show_unfullscreen_button(self):
        if self._is_fullscreen and self.props.enable_fullscreen_mode:
            if not self._unfullscreen_button.props.visible:
                self._unfullscreen_button.show()

            # Reset the timer
            if self._unfullscreen_button_timeout_id is not None:
                GLib.source_remove(self._unfullscreen_button_timeout_id)
                self._unfullscreen_button_timeout_id = None

            self._unfullscreen_button_timeout_id = \
                GLib.timeout_add_seconds(
                    _UNFULLSCREEN_BUTTON_VISIBILITY_TIMEOUT,
                    self.__unfullscreen_button_timeout_cb)

    def __unfullscreen_button_timeout_cb(self):
        self._unfullscreen_button.hide()
        self._unfullscreen_button_timeout_id = None
        return False

    def __request_clear_area_cb(self, activity, osk_rect, cursor_rect):
        self._clear_area_dy = cursor_rect.y + cursor_rect.height - osk_rect.y

        if self._clear_area_dy < 0:
            self._clear_area_dy = 0
            return False

        self.queue_resize()
        return True

    def __unset_clear_area_cb(self, activity, snap_back):
        self._clear_area_dy = 0
        self.queue_resize()
        return True

    def __size_allocate_cb(self, widget, allocation):
        self.set_allocation(allocation)
        allocation.y -= self._clear_area_dy
        self.__vbox.size_allocate(allocation)

    def set_enable_fullscreen_mode(self, enable_fullscreen_mode):
        """
        Set enable fullscreen mode.

        Args:
            enable_fullscreen_mode (bool): enable fullscreen mode
        """
        self._enable_fullscreen_mode = enable_fullscreen_mode

    def get_enable_fullscreen_mode(self):
        """
        Get enable fullscreen mode.

        Returns:
            bool: enable fullscreen mode
        """
        return self._enable_fullscreen_mode

    enable_fullscreen_mode = GObject.Property(
        type=object,
        setter=set_enable_fullscreen_mode,
        getter=get_enable_fullscreen_mode)
    """
    Property: (bool) whether the window is allowed to enter fullscreen
    mode, default True.
    """

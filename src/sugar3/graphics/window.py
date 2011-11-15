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

from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import Gtk
import warnings

from sugar3.graphics.icon import Icon
from sugar3.graphics import palettegroup


_UNFULLSCREEN_BUTTON_VISIBILITY_TIMEOUT = 2


class UnfullscreenButton(Gtk.Window):

    def __init__(self):
        GObject.GObject.__init__(self)

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        self.set_border_width(0)

        self.props.accept_focus = False

        #Setup estimate of width, height
        w, h = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
        self._width = w
        self._height = h

        self.connect('size-request', self._size_request_cb)

        screen = self.get_screen()
        screen.connect('size-changed', self._screen_size_changed_cb)

        self._button = Gtk.Button()
        self._button.set_relief(Gtk.ReliefStyle.NONE)

        self._icon = Icon(icon_name='view-return',
                            icon_size=Gtk.IconSize.LARGE_TOOLBAR)
        self._icon.show()
        self._button.add(self._icon)

        self._button.show()
        self.add(self._button)

    def connect_button_press(self, cb):
        self._button.connect('button-press-event', cb)

    def _reposition(self):
        x = Gdk.Screen.width() - self._width
        self.move(x, 0)

    def _size_request_cb(self, widget, req):
        self._width = req.width
        self._height = req.height
        self._reposition()

    def _screen_size_changed_cb(self, screen):
        self._reposition()


class Window(Gtk.Window):

    def __init__(self, **args):
        self._enable_fullscreen_mode = True

        GObject.GObject.__init__(self, **args)

        self.set_decorated(False)
        self.maximize()
        self.connect('realize', self.__window_realize_cb)
        self.connect('key-press-event', self.__key_press_cb)

        self._toolbar_box = None
        self._alerts = []
        self._canvas = None
        self.tray = None

        self.__vbox = Gtk.VBox()
        self.__hbox = Gtk.HBox()
        self.__vbox.pack_start(self.__hbox, True, True, 0)
        self.__hbox.show()

        self.add_events(Gdk.EventMask.POINTER_MOTION_HINT_MASK
                        | Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect('motion-notify-event', self.__motion_notify_cb)

        self.add(self.__vbox)
        self.__vbox.show()

        self._is_fullscreen = False
        self._unfullscreen_button = UnfullscreenButton()
        self._unfullscreen_button.set_transient_for(self)
        self._unfullscreen_button.connect_button_press(
            self.__unfullscreen_button_pressed)
        self._unfullscreen_button_timeout_id = None

    def reveal(self):
        """ Make window active

        In contrast with present(), brings window to the top
        even after invoking on response on non-gtk events.
        See #1423.
        """
        window = self.get_window()
        if window is None:
            self.show()
            return
        timestamp = Gtk.get_current_event_time()
        if not timestamp:
            timestamp = GdkX11.get_server_time(window)
        window.focus(timestamp)

    def fullscreen(self):
        palettegroup.popdown_all()
        if self._toolbar_box is not None:
            self._toolbar_box.hide()
        if self.tray is not None:
            self.tray.hide()

        self._is_fullscreen = True

        if self.props.enable_fullscreen_mode:
            self._unfullscreen_button.show()

            if self._unfullscreen_button_timeout_id is not None:
                GObject.source_remove(self._unfullscreen_button_timeout_id)
                self._unfullscreen_button_timeout_id = None

            self._unfullscreen_button_timeout_id = \
                GObject.timeout_add_seconds( \
                    _UNFULLSCREEN_BUTTON_VISIBILITY_TIMEOUT, \
                    self.__unfullscreen_button_timeout_cb)

    def unfullscreen(self):
        if self._toolbar_box is not None:
            self._toolbar_box.show()
        if self.tray is not None:
            self.tray.show()

        self._is_fullscreen = False

        if self.props.enable_fullscreen_mode:
            self._unfullscreen_button.hide()

            if self._unfullscreen_button_timeout_id:
                GObject.source_remove(self._unfullscreen_button_timeout_id)
                self._unfullscreen_button_timeout_id = None

    def set_canvas(self, canvas):
        if self._canvas:
            self.__hbox.remove(self._canvas)

        if canvas:
            self.__hbox.pack_start(canvas, True, True, 0)

        self._canvas = canvas
        self.__vbox.set_focus_child(self._canvas)

    def get_canvas(self):
        return self._canvas

    canvas = property(get_canvas, set_canvas)

    def get_toolbar_box(self):
        return self._toolbar_box

    def set_toolbar_box(self, toolbar_box):
        if self._toolbar_box:
            self.__vbox.remove(self._toolbar_box)

        if toolbar_box:
            self.__vbox.pack_start(toolbar_box, False)
            self.__vbox.reorder_child(toolbar_box, 0)

        self._toolbar_box = toolbar_box

    toolbar_box = property(get_toolbar_box, set_toolbar_box)

    def set_tray(self, tray, position):
        if self.tray:
            box = self.tray.get_parent()
            box.remove(self.tray)

        if position == Gtk.PositionType.LEFT:
            self.__hbox.pack_start(tray, False)
        elif position == Gtk.PositionType.RIGHT:
            self.__hbox.pack_end(tray, False)
        elif position == Gtk.PositionType.BOTTOM:
            self.__vbox.pack_end(tray, False)

        self.tray = tray

    def add_alert(self, alert):
        self._alerts.append(alert)
        if len(self._alerts) == 1:
            self.__vbox.pack_start(alert, False)
            if self._toolbar_box is not None:
                self.__vbox.reorder_child(alert, 1)
            else:
                self.__vbox.reorder_child(alert, 0)

    def remove_alert(self, alert):
        if alert in self._alerts:
            self._alerts.remove(alert)
            # if the alert is the visible one on top of the queue
            if alert.get_parent() is not None:
                self.__vbox.remove(alert)
                if len(self._alerts) >= 1:
                    self.__vbox.pack_start(self._alerts[0], False)
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

    def __unfullscreen_button_pressed(self, widget, event):
        self.unfullscreen()

    def __motion_notify_cb(self, widget, event):
        if self._is_fullscreen and self.props.enable_fullscreen_mode:
            if not self._unfullscreen_button.props.visible:
                self._unfullscreen_button.show()
            else:
                # Reset the timer
                if self._unfullscreen_button_timeout_id is not None:
                    GObject.source_remove(self._unfullscreen_button_timeout_id)
                    self._unfullscreen_button_timeout_id = None

                self._unfullscreen_button_timeout_id = \
                    GObject.timeout_add_seconds( \
                        _UNFULLSCREEN_BUTTON_VISIBILITY_TIMEOUT, \
                        self.__unfullscreen_button_timeout_cb)
        return False

    def __unfullscreen_button_timeout_cb(self):
        self._unfullscreen_button.hide()
        self._unfullscreen_button_timeout_id = None
        return False

    def set_enable_fullscreen_mode(self, enable_fullscreen_mode):
        self._enable_fullscreen_mode = enable_fullscreen_mode

    def get_enable_fullscreen_mode(self):
        return self._enable_fullscreen_mode

    enable_fullscreen_mode = GObject.property(type=object,
        setter=set_enable_fullscreen_mode, getter=get_enable_fullscreen_mode)

    # DEPRECATED

    def set_toolbox(self, toolbar_box):
        warnings.warn('use toolbar_box instead of toolbox', DeprecationWarning)
        self.set_toolbar_box(toolbar_box)

    def get_toolbox(self):
        warnings.warn('use toolbar_box instead of toolbox', DeprecationWarning)
        return self._toolbar_box

    toolbox = property(get_toolbox, set_toolbox)

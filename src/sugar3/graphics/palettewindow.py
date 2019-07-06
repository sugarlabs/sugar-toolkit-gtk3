# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
# Copyright (C) 2008, One Laptop Per Child
# Copyright (C) 2009, Tomeu Vizoso
# Copyright (C) 2011, Benjamin Berg <benjamin@sipsolutions.net>
# Copyright (C) 2011, Marco Pesenti Gritti <marco@marcopg.org>
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

import logging
import math

import gi
gi.require_version('SugarGestures', '1.0')

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GLib

from gi.repository import SugarGestures
from sugar3.graphics import palettegroup
from sugar3.graphics import animator
from sugar3.graphics import style
from sugar3.graphics.icon import CellRendererIcon


_pointer = None


def _get_pointer_position(widget):
    global _pointer

    if _pointer is None:
        display = widget.get_display()
        manager = display.get_device_manager()
        _pointer = manager.get_client_pointer()
    screen, x, y = _pointer.get_position()
    return (x, y)


def _calculate_gap(a, b):
    """Helper function to find the gap position and size of widget a"""
    # Test for each side if the palette and invoker are
    # adjacent to each other.
    gap = True

    if a.y + a.height == b.y:
        gap_side = Gtk.PositionType.BOTTOM
    elif a.x + a.width == b.x:
        gap_side = Gtk.PositionType.RIGHT
    elif a.x == b.x + b.width:
        gap_side = Gtk.PositionType.LEFT
    elif a.y == b.y + b.height:
        gap_side = Gtk.PositionType.TOP
    else:
        gap = False

    if gap:
        if gap_side == Gtk.PositionType.BOTTOM or \
                gap_side == Gtk.PositionType.TOP:
            gap_start = min(a.width, max(0, b.x - a.x))
            gap_size = max(0, min(a.width,
                                  (b.x + b.width) - a.x) - gap_start)
        elif gap_side == Gtk.PositionType.RIGHT or \
                gap_side == Gtk.PositionType.LEFT:
            gap_start = min(a.height, max(0, b.y - a.y))
            gap_size = max(0, min(a.height,
                                  (b.y + b.height) - a.y) - gap_start)

    if gap and gap_size > 0:
        return (gap_side, gap_start, gap_size)
    else:
        return False


class _PaletteMenuWidget(Gtk.Menu):

    __gtype_name__ = "SugarPaletteMenuWidget"

    __gsignals__ = {
        'enter-notify': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'leave-notify': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        Gtk.Menu.__init__(self)

        accel_group = Gtk.AccelGroup()
        self.sugar_accel_group = accel_group
        self.get_toplevel().add_accel_group(accel_group)

        self._popup_position = (0, 0)
        self._entered = False
        self._mouse_in_palette = False
        self._mouse_in_invoker = False
        self._up = False
        self._invoker = None
        self._menus = []

    def set_accept_focus(self, focus):
        pass

    def get_origin(self):
        res_, x, y = self.get_toplevel().get_window().get_origin()
        return x, y

    def move(self, x, y):
        self._popup_position = (x, y)

    def set_transient_for(self, window):
        pass

    def set_invoker(self, invoker):
        pass

    def _position(self, widget, *data):
        return self._popup_position[0], self._popup_position[1], False

    def popup(self, invoker):
        if self._up:
            return

        # We need to track certain mouse events in order to close the palette
        # when the mouse leaves the palette and the invoker widget, but
        # GtkMenu makes our lives hard here.
        #
        # GtkMenu takes a grab on the root window, meaning that normal
        # enter/leave events are not sent to the relevant widgets.
        # However, connecting enter-notify and leave-notify events in this
        # GtkMenu subclass mean that we get to see the events being grabbed.
        # With certain filtering in place (see _enter_notify_cb and
        # _leave_notify_cb) we are able to accurately determine when the
        # mouse leaves/enters the palette menu. Some spurious events are
        # generated but the important thing is that the last event generated
        # in response to a user action is always reliable (i.e. we will
        # always get a leave event last if the user left the menu,
        # even if we get some strange enter events leading up to it).
        #
        # This is complicated with submenus; in this case the submenu takes
        # the grab, so we must also listen for events on any submenus of
        # the palette and apply the same considerations.
        #
        # The remaining challenge is tracking when the mouse enters or leaves
        # the invoker area. While the appropriate GtkMenu grab is active,
        # we do get informed of such events, however these events will only
        # arrive if the user has entered the menu. If the user hovers over
        # the invoker and then leaves the invoker without entering the palette,
        # we get no enter/leave event.
        # We work around this by tracking mouse motion events. When the mouse
        # moves, we compare the mouse coordinates to the region occupied by the
        # invoker, and this lets us track enter/leave for the invoker widget.

        self._invoker = invoker
        self._find_all_menus(self)
        self.realize()
        for menu in self._menus:
            if self._invoker:
                menu.connect('motion-notify-event', self._motion_notify_cb)
            menu.connect('enter-notify-event', self._enter_notify_cb)
            menu.connect('leave-notify-event', self._leave_notify_cb)
            menu.connect('button-release-event', self._button_release_event_cb)
        self._entered = False
        self._mouse_in_palette = False
        self._mouse_in_invoker = False
        Gtk.Menu.popup(self, None, None, self._position, None, 0, 0)
        self._up = True

    def popdown(self):
        if not self._up:
            return
        Gtk.Menu.popdown(self)

        for menu in self._menus:
            menu.disconnect_by_func(self._motion_notify_cb)
            menu.disconnect_by_func(self._enter_notify_cb)
            menu.disconnect_by_func(self._leave_notify_cb)

        self._up = False
        self._menus = []
        self._invoker = None

    def _find_all_menus(self, menu):
        """
        Recursively find all submenus of menu, adding them to self._menus.
        """
        self._menus.append(menu)
        for child in menu.get_children():
            if not isinstance(child, Gtk.MenuItem):
                continue
            submenu = child.get_submenu()
            if submenu and isinstance(submenu, Gtk.Menu):
                self._find_all_menus(submenu)

    def _enter_notify_cb(self, widget, event):
        if event.mode in (Gdk.CrossingMode.GRAB, Gdk.CrossingMode.GTK_GRAB):
            return False
        if event.get_source_device().get_source() == \
                Gdk.InputSource.TOUCHSCREEN:
            return False
        if Gtk.get_event_widget(event) not in self._menus:
            return False

        self._mouse_in_palette = True
        self._reevaluate_state()
        return False

    def _leave_notify_cb(self, widget, event):
        if event.mode in (Gdk.CrossingMode.GRAB, Gdk.CrossingMode.GTK_GRAB):
            return False
        if event.get_source_device().get_source() == \
                Gdk.InputSource.TOUCHSCREEN:
            return False
        if Gtk.get_event_widget(event) not in self._menus:
            return False

        self._mouse_in_palette = False
        self._reevaluate_state()
        return False

    def _motion_notify_cb(self, widget, event):
        if event.get_source_device().get_source() == \
                Gdk.InputSource.TOUCHSCREEN:
            return False
        x = event.x_root
        y = event.y_root

        rect = self._invoker.get_rect()
        in_invoker = x >= rect.x and x < (rect.x + rect.width) \
            and y >= rect.y and y < (rect.y + rect.height)

        if in_invoker != self._mouse_in_invoker:
            self._mouse_in_invoker = in_invoker
            self._reevaluate_state()

    def _button_release_event_cb(self, widget, event):
        x = event.x_root
        y = event.y_root

        rect = self._invoker.get_rect()
        in_invoker = x >= rect.x and x < (rect.x + rect.width) \
            and y >= rect.y and y < (rect.y + rect.height)

        if in_invoker:
            return True

    def _reevaluate_state(self):
        if self._entered:
            # If we previously advised that the mouse was inside, but now the
            # mouse is outside both the invoker and the palette, notify that
            # the mouse has left.
            if not self._mouse_in_palette and not self._mouse_in_invoker:
                self._entered = False
                self.emit('leave-notify')
        else:
            # If we previously advised that the mouse had left, but now the
            # mouse is inside either the palette or the invoker, notify that
            # the mouse has entered.
            if self._mouse_in_palette or self._mouse_in_invoker:
                self._entered = True
                self.emit('enter-notify')


class _PaletteWindowWidget(Gtk.Window):

    __gtype_name__ = 'SugarPaletteWindowWidget'

    __gsignals__ = {
        'enter-notify': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'leave-notify': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, palette=None):
        Gtk.Window.__init__(self)

        self._palette = palette
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.NONE)

        context = self.get_style_context()
        # Just assume all borders are the same
        border = context.get_border(Gtk.StateFlags.ACTIVE).right
        self.set_border_width(border)

        accel_group = Gtk.AccelGroup()
        self.sugar_accel_group = accel_group
        self.add_accel_group(accel_group)

        self._old_alloc = None
        self._invoker = None
        self._should_accept_focus = True

    def set_accept_focus(self, focus):
        self._should_accept_focus = focus
        if self.get_window() is not None:
            self.get_window().set_accept_focus(focus)

    def get_origin(self):
        res_, x, y = self.get_window().get_origin()
        return x, y

    def do_realize(self):
        Gtk.Window.do_realize(self)

        self.get_window().set_accept_focus(self._should_accept_focus)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

    def do_get_preferred_width(self):
        minimum, natural = Gtk.Window.do_get_preferred_width(self)
        label_width = 0
        if self._palette is not None:
            label_width = self._palette.get_label_width()
        size = max(natural, label_width + 2 * self.get_border_width(),
                   style.GRID_CELL_SIZE * 3)
        return size, size

    def do_size_allocate(self, allocation):
        Gtk.Window.do_size_allocate(self, allocation)

        if self._old_alloc is None or \
           self._old_alloc.x != allocation.x or \
           self._old_alloc.y != allocation.y or \
           self._old_alloc.width != allocation.width or \
           self._old_alloc.height != allocation.height:
            self.queue_draw()

        # We need to store old allocation because when size_allocate
        # is called widget.allocation is already updated.
        # Gtk.Window resizing is different from normal containers:
        # the X window is resized, widget.allocation is updated from
        # the configure request handler and finally size_allocate is called.
        self._old_alloc = allocation

    def set_invoker(self, invoker):
        self._invoker = invoker

    def get_rect(self):
        win_x, win_y = self.get_origin()
        rectangle = self.get_allocation()

        x = win_x + rectangle.x
        y = win_y + rectangle.y
        minimum, natural = self.get_preferred_size()
        rect = Gdk.Rectangle()
        rect.x = x
        rect.y = y
        rect.width = minimum.width
        rect.height = natural.height

        return rect

    def do_draw(self, cr):
        # Fall trough to the container expose handler.
        # (Leaving out the window expose handler which redraws everything)
        Gtk.Window.do_draw(self, cr)

        if self._invoker is not None and self._invoker.has_rectangle_gap():
            invoker = self._invoker.get_rect()
            palette = self.get_rect()
            gap = _calculate_gap(palette, invoker)
        else:
            gap = False

        allocation = self.get_allocation()
        context = self.get_style_context()
        context.add_class('palette')
        if gap:
            cr.save()
            cr.set_source_rgb(0, 0, 0)
            cr.rectangle(0, 0, allocation.width, allocation.height)
            cr.set_line_width(4)
            cr.stroke()
            cr.restore()
            Gtk.render_frame_gap(
                context, cr, 0, 0, allocation.width, allocation.height,
                gap[0], gap[1], gap[1] + gap[2])
        else:
            Gtk.render_frame(
                context, cr, 0, 0, allocation.width, allocation.height)
        return False

    def __enter_notify_event_cb(self, widget, event):
        if event.mode == Gdk.CrossingMode.NORMAL and \
                event.detail != Gdk.NotifyType.INFERIOR:
            self.emit('enter-notify')
        return False

    def __leave_notify_event_cb(self, widget, event):
        if event.mode != Gdk.CrossingMode.NORMAL:
            return False

        if event.detail != Gdk.NotifyType.INFERIOR:
            self.emit('leave-notify')

    def popup(self, invoker):
        if self.get_visible():
            return
        self.connect('enter-notify-event', self.__enter_notify_event_cb)
        self.connect('leave-notify-event', self.__leave_notify_event_cb)
        self.show()

    def popdown(self):
        if not self.get_visible():
            return
        self.disconnect_by_func(self.__enter_notify_event_cb)
        self.disconnect_by_func(self.__leave_notify_event_cb)
        self.hide()


if hasattr(_PaletteWindowWidget, 'set_css_name'):
    _PaletteWindowWidget.set_css_name('palette')


class MouseSpeedDetector(GObject.GObject):

    __gsignals__ = {
        'motion-slow': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'motion-fast': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    _MOTION_SLOW = 1
    _MOTION_FAST = 2

    def __init__(self, delay, thresh):
        """Create MouseSpeedDetector object,
            delay in msec
            threshold in pixels (per tick of 'delay' msec)"""

        GObject.GObject.__init__(self)

        self.parent = None
        self._threshold = thresh
        self._delay = delay
        self._state = None
        self._timeout_hid = None
        self._mouse_pos = None

    def start(self):
        self.stop()

        self._mouse_pos = _get_pointer_position(self.parent)
        self._timeout_hid = GLib.timeout_add(self._delay, self._timer_cb)

    def stop(self):
        if self._timeout_hid is not None:
            GLib.source_remove(self._timeout_hid)
            self._timeout_hid = None
        self._state = None

    def _detect_motion(self):
        oldx, oldy = self._mouse_pos
        (x, y) = _get_pointer_position(self.parent)
        self._mouse_pos = (x, y)

        dist2 = (oldx - x) ** 2 + (oldy - y) ** 2
        if dist2 > self._threshold ** 2:
            return True
        else:
            return False

    def _timer_cb(self):
        motion = self._detect_motion()
        if motion and self._state != self._MOTION_FAST:
            self.emit('motion-fast')
            self._state = self._MOTION_FAST
        elif not motion and self._state != self._MOTION_SLOW:
            self.emit('motion-slow')
            self._state = self._MOTION_SLOW

        return True


class PaletteWindow(GObject.GObject):
    """
    Base class for _ToolbarPalette and Palette.

    Provides basic management of child widget, invoker, and animation.
    """

    __gsignals__ = {
        'popup': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'popdown': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, **kwargs):
        self._group_id = None
        self._invoker = None
        self._invoker_hids = []
        self._cursor_x = 0
        self._cursor_y = 0
        self._alignment = None
        self._up = False
        self._widget = None

        self._popup_anim = animator.Animator(.5, 10)
        self._popup_anim.add(_PopupAnimation(self))

        self._popdown_anim = animator.Animator(0.6, 10)
        self._popdown_anim.add(_PopdownAnimation(self))

        GObject.GObject.__init__(self, **kwargs)

        self.set_group_id('default')

        self._mouse_detector = MouseSpeedDetector(200, 5)

    def _setup_widget(self):
        self._widget.connect('show', self.__show_cb)
        self._widget.connect('hide', self.__hide_cb)
        self._widget.connect('destroy', self.__destroy_cb)
        self._widget.connect('enter-notify', self.__enter_notify_cb)
        self._widget.connect('leave-notify', self.__leave_notify_cb)
        self._widget.connect('key-press-event', self.__key_press_event_cb)

        self._set_effective_group_id(self._group_id)
        self._widget.set_invoker(self._invoker)

        self._mouse_detector.connect('motion-slow', self._mouse_slow_cb)
        self._mouse_detector.parent = self._widget

    def _teardown_widget(self):
        self._widget.disconnect_by_func(self.__show_cb)
        self._widget.disconnect_by_func(self.__hide_cb)
        self._widget.disconnect_by_func(self.__destroy_cb)
        self._widget.disconnect_by_func(self.__enter_notify_cb)
        self._widget.disconnect_by_func(self.__leave_notify_cb)
        self._widget.disconnect_by_func(self.__key_press_event_cb)
        self._set_effective_group_id(None)

    def destroy(self):
        if self._widget is not None:
            self._widget.destroy()

    def __destroy_cb(self, palette):
        self._mouse_detector.disconnect_by_func(self._mouse_slow_cb)

    def set_invoker(self, invoker):
        for hid in self._invoker_hids[:]:
            self._invoker.disconnect(hid)
            self._invoker_hids.remove(hid)

        self._invoker = invoker
        if self._widget is not None:
            self._widget.set_invoker(invoker)
        if invoker is not None:
            self._invoker_hids.append(self._invoker.connect(
                'mouse-enter', self._invoker_mouse_enter_cb))
            self._invoker_hids.append(self._invoker.connect(
                'mouse-leave', self._invoker_mouse_leave_cb))
            self._invoker_hids.append(self._invoker.connect(
                'right-click', self._invoker_right_click_cb))
            self._invoker_hids.append(self._invoker.connect(
                'toggle-state', self._invoker_toggle_state_cb))

    def get_invoker(self):
        return self._invoker

    invoker = GObject.Property(type=object,
                               getter=get_invoker,
                               setter=set_invoker)

    def _mouse_slow_cb(self, widget):
        self._mouse_detector.stop()
        self._palette_do_popup()

    def _palette_do_popup(self):
        immediate = False

        if self.is_up():
            self._popdown_anim.stop()
            return

        if self._group_id:
            group = palettegroup.get_group(self._group_id)
            if group and group.is_up():
                immediate = True
                group.popdown()

        self.popup(immediate=immediate)

    def is_up(self):
        return self._up

    def _set_effective_group_id(self, group_id):
        if self._group_id:
            group = palettegroup.get_group(self._group_id)
            group.remove(self)
        if group_id:
            group = palettegroup.get_group(group_id)
            group.add(self)

    def set_group_id(self, group_id):
        self._set_effective_group_id(group_id)
        self._group_id = group_id

    def get_group_id(self):
        return self._group_id

    group_id = GObject.Property(type=str,
                                getter=get_group_id,
                                setter=set_group_id)

    def update_position(self):
        invoker = self._invoker
        if invoker is None or self._alignment is None:
            logging.error('Cannot update the palette position.')
            return

        if self._widget is None:
            return

        req = self._widget.size_request()
        if isinstance(self._widget, _PaletteMenuWidget):
            # on Gtk 3.10, menu at the bottom of the screen are resized
            # to not fall out, and report a wrong size.
            # measure the children and move the menu - SL #4673
            total_height = 0
            for child in self._widget.get_children():
                child_req = child.size_request()
                total_height += child_req.height

            # need add the border line width as defined in sugar-artwork
            line_width = 2
            total_height += line_width * 2
            req.height = total_height

        position = invoker.get_position_for_alignment(self._alignment, req)
        if position is None:
            position = invoker.get_position(req)

        self._widget.move(position.x, position.y)

    def get_full_size_request(self):
        return self._widget.size_request()

    def popup(self, immediate=False):
        if self._widget is None:
            return
        if self._invoker is not None:
            full_size_request = self.get_full_size_request()
            self._alignment = self._invoker.get_alignment(full_size_request)

            self.update_position()
            try:
                self._widget.set_transient_for(self._invoker.get_toplevel())
            except TypeError:
                # the expected parent window did likely change e.g. SL #4221
                # popdown the Palette
                self.emit('popdown')
                return

        self._popdown_anim.stop()

        if not immediate:
            self._popup_anim.start()
        else:
            self._popup_anim.stop()
            self._widget.popup(self._invoker)
            # we have to invoke update_position() twice
            # since WM could ignore first move() request
            self.update_position()

    def popdown(self, immediate=False):
        self._popup_anim.stop()
        self._mouse_detector.stop()

        if not immediate:
            self._popdown_anim.start()
        else:
            self._popdown_anim.stop()
            if self._widget is not None:
                self._widget.popdown()

    def on_invoker_enter(self):
        self._popdown_anim.stop()
        self._mouse_detector.start()

    def on_invoker_leave(self):
        self._mouse_detector.stop()
        self.popdown()

    def on_enter(self):
        self._popdown_anim.stop()

    def on_leave(self):
        self.popdown()

    def _invoker_mouse_enter_cb(self, invoker):
        if not self._invoker.locked:
            self.on_invoker_enter()

    def _invoker_mouse_leave_cb(self, invoker):
        if not self._invoker.locked:
            self.on_invoker_leave()

    def _invoker_right_click_cb(self, invoker):
        self.popup(immediate=True)

    def _invoker_toggle_state_cb(self, invoker):
        if self.is_up():
            self.popdown(immediate=True)
        else:
            self.popup(immediate=True)

    def __enter_notify_cb(self, widget):
        if not self._invoker.locked:
            self.on_enter()

    def __leave_notify_cb(self, widget):
        if not self._invoker.locked:
            self.on_leave()

    def __key_press_event_cb(self, window, event):
        if event.keyval == Gdk.KEY_Escape:
            self.popdown()

    def __show_cb(self, widget):
        if self._invoker is not None:
            self._invoker.notify_popup()

        self._up = True
        self.emit('popup')

    def __hide_cb(self, widget):
        if self._invoker:
            self._invoker.notify_popdown()

        self._up = False
        self.emit('popdown')

    def get_rect(self):
        win_x, win_y = self._widget.get_origin()
        rectangle = self._widget.get_allocation()

        x = win_x + rectangle.x
        y = win_y + rectangle.y
        minimum, natural_ = self._widget.get_preferred_size()

        rect = Gdk.Rectangle()
        rect.x = x
        rect.y = y
        rect.width = minimum.width
        rect.height = minimum.height

        return rect


class _PopupAnimation(animator.Animation):

    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette.popup(immediate=True)


class _PopdownAnimation(animator.Animation):

    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette.popdown(immediate=True)


class Invoker(GObject.GObject):

    __gtype_name__ = 'SugarPaletteInvoker'

    __gsignals__ = {
        'mouse-enter': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'mouse-leave': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'right-click': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'toggle-state': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'focus-out': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    ANCHORED = 0
    AT_CURSOR = 1

    BOTTOM = [(0.0, 0.0, 0.0, 1.0), (-1.0, 0.0, 1.0, 1.0)]
    RIGHT = [(0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 1.0, 1.0)]
    TOP = [(0.0, -1.0, 0.0, 0.0), (-1.0, -1.0, 1.0, 0.0)]
    LEFT = [(-1.0, 0.0, 0.0, 0.0), (-1.0, -1.0, 0.0, 1.0)]

    def __init__(self):
        GObject.GObject.__init__(self)

        self.parent = None

        self._screen_area = Gdk.Rectangle()
        self._screen_area.x = self._screen_area.y = 0
        self._screen_area.width = Gdk.Screen.width()
        self._screen_area.height = Gdk.Screen.height()
        self._position_hint = self.ANCHORED
        self._cursor_x = -1
        self._cursor_y = -1
        self._palette = None
        self._cache_palette = True
        self._toggle_palette = False
        self._lock_palette = False
        self.locked = False

    def attach(self, parent):
        self.parent = parent

    def detach(self):
        self.parent = None
        if self._palette is not None:
            self._palette.destroy()
            self._palette = None

    def _get_position_for_alignment(self, alignment, palette_dim):
        palette_halign = alignment[0]
        palette_valign = alignment[1]
        invoker_halign = alignment[2]
        invoker_valign = alignment[3]

        if self._cursor_x == -1 or self._cursor_y == -1:
            position = _get_pointer_position(self.parent)
            (self._cursor_x, self._cursor_y) = position

        if self._position_hint is self.ANCHORED:
            rect = self.get_rect()
        else:
            dist = style.PALETTE_CURSOR_DISTANCE
            rect = Gdk.Rectangle()
            rect.x = self._cursor_x - dist
            rect.y = self._cursor_y - dist
            rect.width = rect.height = dist * 2

        palette_width, palette_height = palette_dim.width, palette_dim.height

        x = rect.x + rect.width * invoker_halign + \
            palette_width * palette_halign

        y = rect.y + rect.height * invoker_valign + \
            palette_height * palette_valign

        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = palette_width
        rect.height = palette_height
        return rect

    def _in_screen(self, rect):
        return rect.x >= self._screen_area.x and \
            rect.y >= self._screen_area.y and \
            rect.x + rect.width <= self._screen_area.width and \
            rect.y + rect.height <= self._screen_area.height

    def _get_area_in_screen(self, rect):
        """Return area of rectangle visible in the screen"""

        x1 = max(rect.x, self._screen_area.x)
        y1 = max(rect.y, self._screen_area.y)
        x2 = min(rect.x + rect.width,
                 self._screen_area.x + self._screen_area.width)
        y2 = min(rect.y + rect.height,
                 self._screen_area.y + self._screen_area.height)

        return (x2 - x1) * (y2 - y1)

    def _get_alignments(self):
        if self._position_hint is self.AT_CURSOR:
            return [(0.0, 0.0, 1.0, 1.0),
                    (0.0, -1.0, 1.0, 0.0),
                    (-1.0, -1.0, 0.0, 0.0),
                    (-1.0, 0.0, 0.0, 1.0)]
        else:
            return self.BOTTOM + self.RIGHT + self.TOP + self.LEFT

    def get_position_for_alignment(self, alignment, palette_dim):
        rect = self._get_position_for_alignment(alignment, palette_dim)
        if self._in_screen(rect):
            return rect
        else:
            return None

    def get_position(self, palette_dim):
        alignment = self.get_alignment(palette_dim)
        rect = self._get_position_for_alignment(alignment, palette_dim)

        # In case our efforts to find an optimum place inside the screen
        # failed, just make sure the palette fits inside the screen if at all
        # possible.
        rect.x = max(0, rect.x)
        rect.y = max(0, rect.y)

        rect.x = min(rect.x, self._screen_area.width - rect.width)
        rect.y = min(rect.y, self._screen_area.height - rect.height)

        return rect

    def get_alignment(self, palette_dim):
        best_alignment = None
        best_area = -1
        for alignment in self._get_alignments():
            pos = self._get_position_for_alignment(alignment, palette_dim)
            if self._in_screen(pos):
                return alignment

            area = self._get_area_in_screen(pos)
            if area > best_area:
                best_alignment = alignment
                best_area = area

        # Palette horiz/vert alignment
        ph = best_alignment[0]
        pv = best_alignment[1]

        # Invoker horiz/vert alignment
        ih = best_alignment[2]
        iv = best_alignment[3]

        rect = self.get_rect()
        screen_area = self._screen_area

        if best_alignment in self.LEFT or best_alignment in self.RIGHT:
            dtop = rect.y - screen_area.y
            dbottom = screen_area.y + screen_area.height - rect.y - rect.width

            iv = 0

            # Set palette_valign to align to screen on the top
            if dtop > dbottom:
                pv = -float(dtop) / palette_dim.height

            # Set palette_valign to align to screen on the bottom
            else:
                pv = -float(palette_dim.height - dbottom - rect.height) \
                    / palette_dim.height

        elif best_alignment in self.TOP or best_alignment in self.BOTTOM:
            dleft = rect.x - screen_area.x
            dright = screen_area.x + screen_area.width - rect.x - rect.width

            ih = 0

            if palette_dim.width == 0:
                ph = 0

            else:
                # Set palette_halign to align to screen on left
                if dleft > dright:
                    ph = -float(dleft) / palette_dim.width

                # Set palette_halign to align to screen on right
                else:
                    ph = -float(palette_dim.width - dright - rect.width) \
                        / palette_dim.width

        return (ph, pv, ih, iv)

    def has_rectangle_gap(self):
        return False

    def draw_rectangle(self, event, palette):
        pass

    def notify_popup(self):
        pass

    def notify_popdown(self):
        self._cursor_x = -1
        self._cursor_y = -1

    def _ensure_palette_exists(self):
        if self.parent and self.palette is None:
            palette = self.parent.create_palette()
            if palette is not None:
                self.palette = palette

    def notify_mouse_enter(self):
        self._ensure_palette_exists()
        self.emit('mouse-enter')

    def notify_mouse_leave(self):
        self.emit('mouse-leave')

    def notify_right_click(self, x=None, y=None):
        '''
        Notify the palette invoker of a right click and expand the
        palette as required.  The x and y args should be that of
        where the event happened, relative to the root of the screen.

        Args
            x (float): the x coord of the event relative to the root
                of the screen, eg. :class:`Gdk.EventTouch.x_root`
            y (float): the y coord of the event relative to the root
                of the screen, eg. :class:`Gdk.EventTouch.y_root`
        '''
        self._ensure_palette_exists()
        self._process_event(x, y)
        self.emit('right-click')

    def notify_toggle_state(self):
        self._ensure_palette_exists()
        self.emit('toggle-state')

    def _process_event(self, x, y):
        if x is None or y is None:
            return

        self._cursor_x = x
        self._cursor_y = y

    def get_palette(self):
        return self._palette

    def set_palette(self, palette):
        if self._palette is not None:
            self._palette.popdown(immediate=True)
            self._palette.props.invoker = None
            # GTK pops down the palette before it invokes the actions on the
            # menu item. We need to postpone destruction of the palette until
            # after all signals have propagated from the menu item to the
            # palette owner.
            GLib.idle_add(lambda old_palette=self._palette:
                          old_palette.destroy(),
                          priority=GLib.PRIORITY_LOW)

        self._palette = palette

        if self._palette is not None:
            self._palette.props.invoker = self
            self._palette.connect('popdown', self.__palette_popdown_cb)

    palette = GObject.Property(
        type=object, setter=set_palette, getter=get_palette)

    def get_cache_palette(self):
        return self._cache_palette

    def set_cache_palette(self, cache_palette):
        self._cache_palette = cache_palette

    cache_palette = GObject.Property(type=object, setter=set_cache_palette,
                                     getter=get_cache_palette)
    """Whether the invoker will cache the palette after its creation. Defaults
    to True.
    """

    def get_toggle_palette(self):
        return self._toggle_palette

    def set_toggle_palette(self, toggle_palette):
        self._toggle_palette = toggle_palette

    toggle_palette = GObject.Property(type=object, setter=set_toggle_palette,
                                      getter=get_toggle_palette)
    """Whether the invoker will popup/popdown the Palette on
    button left click/touch tap. Defaults to False.
    """

    def get_lock_palette(self):
        return self._lock_palette

    def set_lock_palette(self, lock_palette):
        self._lock_palette = lock_palette

    lock_palette = GObject.Property(type=object, setter=set_lock_palette,
                                    getter=get_lock_palette)
    """Whether the invoker will lock the Palette and
    ignore mouse events. Defaults to False.
    """

    def __palette_popdown_cb(self, palette):
        if not self.props.cache_palette:
            self.set_palette(None)

    def primary_text_clicked(self):
        """Implemented by invokers that can be clicked"""
        pass


class WidgetInvoker(Invoker):

    def __init__(self, parent=None, widget=None):
        Invoker.__init__(self)

        self._widget = None
        self._expanded = False
        self._pointer_position = (-1, -1)
        self._enter_hid = None
        self._leave_hid = None
        self._release_hid = None
        self._click_hid = None
        self._touch_hid = None
        self._draw_hid = None
        self._long_pressed_recognized = False
        self._long_pressed_hid = None
        self._long_pressed_controller = SugarGestures.LongPressController()

        if parent or widget:
            self.attach_widget(parent, widget)

    def attach_widget(self, parent, widget=None):
        if widget:
            self._widget = widget
        else:
            self._widget = parent

        self._pointer_position = _get_pointer_position(self._widget)

        self.notify('widget')

        self._enter_hid = self._widget.connect('enter-notify-event',
                                               self.__enter_notify_event_cb)
        self._leave_hid = self._widget.connect('leave-notify-event',
                                               self.__leave_notify_event_cb)
        if GObject.signal_lookup('clicked', self._widget) != 0:
            self._click_hid = self._widget.connect('clicked',
                                                   self.__click_event_cb)
        self._touch_hid = self._widget.connect('touch-event',
                                               self.__touch_event_cb)
        self._release_hid = \
            self._widget.connect('button-release-event',
                                 self.__button_release_event_cb)
        self._draw_hid = self._widget.connect_after('draw', self.__drawing_cb)

        self._long_pressed_hid = self._long_pressed_controller.connect(
            'pressed', self.__long_pressed_event_cb, self._widget)
        self._long_pressed_controller.attach(
            self._widget,
            SugarGestures.EventControllerFlags.NONE)

        self.attach(parent)

    def detach(self):
        Invoker.detach(self)
        self._widget.disconnect(self._enter_hid)
        self._widget.disconnect(self._leave_hid)
        self._widget.disconnect(self._release_hid)
        self._widget.disconnect(self._draw_hid)
        if self._click_hid:
            self._widget.disconnect(self._click_hid)
        self._widget.disconnect(self._touch_hid)
        self._long_pressed_controller.detach(self._widget)
        self._long_pressed_controller.disconnect(self._long_pressed_hid)

    def get_rect(self):
        allocation = self._widget.get_allocation()
        window = self._widget.get_window()
        if window is not None:
            res_, x, y = window.get_origin()
        else:
            logging.warning(
                "Trying to position palette with invoker that's not realized.")
            x = 0
            y = 0

        if not self._widget.get_has_window():
            x += allocation.x
            y += allocation.y

        rect = Gdk.Rectangle()
        rect.x = x
        rect.y = y
        rect.width = allocation.width
        rect.height = allocation.height
        return rect

    def has_rectangle_gap(self):
        return True

    def draw_rectangle(self, cr, palette):
        allocation = self.parent.get_allocation()

        context = self.parent.get_style_context()
        context.add_class('toolitem')
        context.add_class('palette-down')

        gap = _calculate_gap(self.get_rect(), palette.get_rect())
        if gap:
            Gtk.render_frame_gap(context, cr, 0, 0,
                                 allocation.width,
                                 allocation.height,
                                 gap[0], gap[1], gap[1] + gap[2])

    def __enter_notify_event_cb(self, widget, event):
        if (event.x_root, event.y_root) == self._pointer_position:
            self._pointer_position = (-1, -1)
            return False
        if event.mode == Gdk.CrossingMode.NORMAL:
            self.notify_mouse_enter()

    def __leave_notify_event_cb(self, widget, event):
        if event.mode == Gdk.CrossingMode.NORMAL:
            self.notify_mouse_leave()

    def __touch_event_cb(self, button, event):
        if event.type == Gdk.EventType.TOUCH_END:
            if self._long_pressed_recognized:
                self._long_pressed_recognized = False
                return True
        return False

    def __click_event_cb(self, button):
        event = Gtk.get_current_event()
        if not event:
            # not an event from a user interaction, this can be when
            # the clicked event is emitted on a 'active' property
            # change of ToggleToolButton for example
            return
        if event and button != Gtk.get_event_widget(event):
            # another special case for the ToggleToolButton: this handles
            # the case where we select an item and the active property
            # of the other one changes to 'False'
            return

        if self.props.lock_palette and not self.locked:
            self.locked = True
            if hasattr(self.parent, 'set_expanded'):
                self.parent.set_expanded(True)

        if self.props.toggle_palette:
            self.notify_toggle_state()

    def __button_release_event_cb(self, widget, event):
        if event.button == 1 and not self._click_hid:
            if self.props.lock_palette and not self.locked:
                self.locked = True
                if hasattr(self.parent, 'set_expanded'):
                    self.parent.set_expanded(True)

            if self.props.toggle_palette:
                self.notify_toggle_state()
        elif event.button == 3:
            self.notify_right_click(event.x_root, event.y_root)
            return True
        else:
            return False

    def __long_pressed_event_cb(self, controller, x, y, widget):
        self._long_pressed_recognized = True
        self.notify_right_click(x, y)

    def get_toplevel(self):
        return self._widget.get_toplevel()

    def notify_popup(self):
        Invoker.notify_popup(self)
        self._widget.queue_draw()

    def notify_popdown(self):
        self.locked = False
        Invoker.notify_popdown(self)
        self._widget.queue_draw()

    def _get_widget(self):
        return self._widget
    widget = GObject.Property(type=object, getter=_get_widget, setter=None)

    def __drawing_cb(self, widget, cr):
        if not self.props.lock_palette:
            return False
        alloc = widget.get_allocation()
        arrow_size = style.TOOLBAR_ARROW_SIZE / 2
        y = alloc.height - arrow_size
        x = (alloc.width - arrow_size) / 2
        context = widget.get_style_context()
        context.add_class('toolitem')
        if self.locked:
            Gtk.render_arrow(context, cr, 0, x, y, arrow_size)
        else:
            Gtk.render_arrow(context, cr, math.pi, x, y, arrow_size)


class CursorInvoker(Invoker):

    def __init__(self, parent=None):
        Invoker.__init__(self)

        self._position_hint = self.AT_CURSOR
        self._pointer_position = (-1, -1)
        self._enter_hid = None
        self._leave_hid = None
        self._release_hid = None
        self._item = None
        self._long_pressed_recognized = False
        self._long_pressed_hid = None
        self._long_pressed_controller = SugarGestures.LongPressController()

        if parent:
            self.attach(parent)

    def attach(self, parent):
        Invoker.attach(self, parent)

        self._item = parent

        self._pointer_position = _get_pointer_position(self.parent)

        self._enter_hid = self._item.connect('enter-notify-event',
                                             self.__enter_notify_event_cb)
        self._leave_hid = self._item.connect('leave-notify-event',
                                             self.__leave_notify_event_cb)
        self._release_hid = self._item.connect('button-release-event',
                                               self.__button_release_event_cb)
        self._long_pressed_hid = self._long_pressed_controller.connect(
            'pressed',
            self.__long_pressed_event_cb, self._item)
        self._long_pressed_controller.attach(
            self._item,
            SugarGestures.EventControllerFlags.NONE)

    def detach(self):
        Invoker.detach(self)
        self._item.disconnect_by_func(self.__enter_notify_event_cb)
        self._item.disconnect_by_func(self.__leave_notify_event_cb)
        self._item.disconnect_by_func(self.__button_release_event_cb)
        self._long_pressed_controller.detach(self._item)
        self._long_pressed_controller.disconnect(self._long_pressed_hid)

    def get_default_position(self):
        return self.AT_CURSOR

    def get_rect(self):
        window = self._item.get_window()
        allocation = self._item.get_allocation()
        rect = Gdk.Rectangle()
        rect.x, rect.y = window.get_root_coords(allocation.x, allocation.y)
        rect.width = allocation.width
        rect.height = allocation.height
        return rect

    def __enter_notify_event_cb(self, button, event):
        if (event.x_root, event.y_root) == self._pointer_position:
            self._pointer_position = (-1, -1)
            return False
        if event.mode == Gdk.CrossingMode.NORMAL:
            self.notify_mouse_enter()
        return False

    def __leave_notify_event_cb(self, button, event):
        if event.mode == Gdk.CrossingMode.NORMAL:
            self.notify_mouse_leave()
        return False

    def __button_release_event_cb(self, button, event):
        # check if the release is done outside of the parent widget
        alloc = self._item.get_allocation()
        if not (0 < event.x < alloc.width and 0 < event.y < alloc.height):
            return False

        if self._long_pressed_recognized:
            self._long_pressed_recognized = False
            return True
        if event.button == 1:
            if self.props.toggle_palette:
                self.notify_toggle_state()
        if event.button == 3:
            self.notify_right_click(event.x_root, event.y_root)
            return True
        else:
            return False

    def __long_pressed_event_cb(self, controller, x, y, widget):
        self._long_pressed_recognized = True
        x, y = widget.get_window().get_root_coords(x, y)
        self.notify_right_click(x, y)

    def get_toplevel(self):
        return self._item.get_toplevel()


class ToolInvoker(WidgetInvoker):
    '''
    A palette invoker for toolbar buttons and other items.  This invoker
    will properly align the palette so that is perpendicular to the toolbar
    (a horizontal toolbar will spawn a palette going downwards).  It also
    draws the highlights specific to a toolitem.

    For :class:`sugar3.graphics.toolbutton.ToolButton` and subclasses, you
    should not use the toolinvoker directly.  Instead, just subclass the
    tool button and override the `create_palette` function.

    Args:
        parent (Gtk.Widget):  toolitem to connect invoker to
    '''

    def __init__(self, parent=None):
        WidgetInvoker.__init__(self)
        self._tool = None

        if parent:
            self.attach_tool(parent)

    def attach_tool(self, widget):
        '''
        Attach a toolitem to the invoker.  Same behaviour as passing the
        `parent` argument to the constructor.

        Args:
            widget (Gtk.Widget):  toolitem to connect invoker to
        '''
        self._tool = widget
        self.attach_widget(widget, widget.get_child())

    def _get_alignments(self):
        parent = self._widget.get_parent()
        if parent is None:
            return WidgetInvoker._get_alignments(self)

        if parent.get_orientation() is Gtk.Orientation.HORIZONTAL:
            return self.BOTTOM + self.TOP
        else:
            return self.LEFT + self.RIGHT

    def primary_text_clicked(self):
        self._widget.emit('clicked')

    def notify_popup(self):
        WidgetInvoker.notify_popup(self)
        self._tool.queue_draw()

    def notify_popdown(self):
        WidgetInvoker.notify_popdown(self)
        self._tool.queue_draw()


class TreeViewInvoker(Invoker):
    def __init__(self):
        Invoker.__init__(self)

        self._tree_view = None
        self._motion_hid = None
        self._release_hid = None
        self._long_pressed_hid = None
        self._position_hint = self.AT_CURSOR

        self._long_pressed_controller = SugarGestures.LongPressController()

        self._tree_view = None
        self._path = None
        self._column = None

        self.palette = None

    def attach_treeview(self, tree_view):
        self._tree_view = tree_view

        self._motion_hid = tree_view.connect('motion-notify-event',
                                             self.__motion_notify_event_cb)
        self._release_hid = tree_view.connect('button-release-event',
                                              self.__button_release_event_cb)
        self._long_pressed_hid = self._long_pressed_controller.connect(
            'pressed', self.__long_pressed_event_cb, tree_view)
        self._long_pressed_controller.attach(
            tree_view,
            SugarGestures.EventControllerFlags.NONE)

        Invoker.attach(self, tree_view)

    def detach(self):
        Invoker.detach(self)
        self._tree_view.disconnect(self._motion_hid)
        self._tree_view.disconnect(self._release_hid)
        self._long_pressed_controller.detach(self._tree_view)
        self._long_pressed_controller.disconnect(self._long_pressed_hid)

    def get_rect(self):
        return self._tree_view.get_background_area(self._path, self._column)

    def get_toplevel(self):
        return self._tree_view.get_toplevel()

    def __motion_notify_event_cb(self, widget, event):
        here = self._tree_view.get_path_at_pos(int(event.x), int(event.y))
        if here is None:
            if self._path is not None:
                self.notify_mouse_leave()
            self._path = None
            self._column = None
            return

        path, column, x_, y_ = here
        if path != self._path or column != self._column:
            self._redraw_cell(self._path, self._column)
            self._redraw_cell(path, column)

            self._path = path
            self._column = column

            if self.palette is not None:
                self.palette.popdown(immediate=True)
                self.palette = None

            self.notify_mouse_enter()

    def _redraw_cell(self, path, column):
        area = self._tree_view.get_background_area(path, column)
        x, y = \
            self._tree_view.convert_bin_window_to_widget_coords(area.x, area.y)
        self._tree_view.queue_draw_area(x, y, area.width, area.height)

    def __button_release_event_cb(self, widget, event):
        x, y = int(event.x), int(event.y)
        here = self._tree_view.get_path_at_pos(x, y)
        if here is None:
            return False
        path, column, cell_x, cell_y = here
        self._path = path
        self._column = column
        if event.button == 1:
            # left mouse button
            if self.palette is not None:
                self.palette.popdown(immediate=True)
            # NOTE: we don't use columns with more than one cell
            cellrenderer = column.get_cells()[0]
            if cellrenderer is not None and \
                    isinstance(cellrenderer, CellRendererIcon):
                cellrenderer.emit('clicked', path)
            # So the treeview receives it and knows a drag isn't going on
            return False
        elif event.button == 3:
            # right mouse button
            self._ensure_palette_exists()
            self.notify_right_click(event.x_root, event.y_root)
            return True
        else:
            return False

    def __long_pressed_event_cb(self, controller, x, y, widget):
        path, column, x_, y_ = self._tree_view.get_path_at_pos(x, y)
        self._path = path
        self._column = column
        self._ensure_palette_exists()
        self.notify_right_click(x, y)

    def _ensure_palette_exists(self):
        if hasattr(self._tree_view, 'create_palette'):
            self.palette = self._tree_view.create_palette(
                self._path, self._column)
        else:
            self.palette = None

    def notify_popdown(self):
        Invoker.notify_popdown(self)
        self.palette = None

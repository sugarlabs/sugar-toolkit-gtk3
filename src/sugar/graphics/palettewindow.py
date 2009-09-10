# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
# Copyright (C) 2008, One Laptop Per Child
# Copyright (C) 2009, Tomeu Vizoso
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

import gtk
import gobject
import hippo

from sugar.graphics import palettegroup
from sugar.graphics import animator
from sugar.graphics import style


def _calculate_gap(a, b):
    """Helper function to find the gap position and size of widget a"""
    # Test for each side if the palette and invoker are
    # adjacent to each other.
    gap = True

    if a.y + a.height == b.y:
        gap_side = gtk.POS_BOTTOM
    elif a.x + a.width == b.x:
        gap_side = gtk.POS_RIGHT
    elif a.x == b.x + b.width:
        gap_side = gtk.POS_LEFT
    elif a.y == b.y + b.height:
        gap_side = gtk.POS_TOP
    else:
        gap = False

    if gap:
        if gap_side == gtk.POS_BOTTOM or gap_side == gtk.POS_TOP:
            gap_start = min(a.width, max(0, b.x - a.x))
            gap_size = max(0, min(a.width,
                                  (b.x + b.width) - a.x) - gap_start)
        elif gap_side == gtk.POS_RIGHT or gap_side == gtk.POS_LEFT:
            gap_start = min(a.height, max(0, b.y - a.y))
            gap_size = max(0, min(a.height,
                                  (b.y + b.height) - a.y) - gap_start)

    if gap and gap_size > 0:
        return (gap_side, gap_start, gap_size)
    else:
        return False


class MouseSpeedDetector(gobject.GObject):

    __gsignals__ = {
        'motion-slow': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'motion-fast': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
    }

    _MOTION_SLOW = 1
    _MOTION_FAST = 2

    def __init__(self, parent, delay, thresh):
        """Create MouseSpeedDetector object,
            delay in msec
            threshold in pixels (per tick of 'delay' msec)"""

        gobject.GObject.__init__(self)

        self._threshold = thresh
        self._parent = parent
        self._delay = delay
        self._state = None
        self._timeout_hid = None
        self._mouse_pos = None

    def start(self):
        self.stop()

        self._mouse_pos = self._get_mouse_position()
        self._timeout_hid = gobject.timeout_add(self._delay, self._timer_cb)

    def stop(self):
        if self._timeout_hid is not None:
            gobject.source_remove(self._timeout_hid)
        self._state = None

    def _get_mouse_position(self):
        display = gtk.gdk.display_get_default()
        screen_, x, y, mask_ = display.get_pointer()
        return (x, y)

    def _detect_motion(self):
        oldx, oldy = self._mouse_pos
        (x, y) = self._get_mouse_position()
        self._mouse_pos = (x, y)

        dist2 = (oldx - x)**2 + (oldy - y)**2
        if dist2 > self._threshold**2:
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


class PaletteWindow(gtk.Window):

    __gtype_name__ = 'SugarPaletteWindow'

    __gsignals__ = {
        'popup': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'popdown': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'activate': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
    }

    def __init__(self, **kwargs):
        self._group_id = None
        self._invoker = None
        self._invoker_hids = []
        self._cursor_x = 0
        self._cursor_y = 0
        self._alignment = None
        self._up = False
        self._old_alloc = None

        self._popup_anim = animator.Animator(.5, 10)
        self._popup_anim.add(_PopupAnimation(self))

        self._popdown_anim = animator.Animator(0.6, 10)
        self._popdown_anim.add(_PopdownAnimation(self))

        gobject.GObject.__init__(self, **kwargs)

        self.set_decorated(False)
        self.set_resizable(False)
        # Just assume xthickness and ythickness are the same
        self.set_border_width(self.get_style().xthickness)

        accel_group = gtk.AccelGroup()
        self.set_data('sugar-accel-group', accel_group)
        self.add_accel_group(accel_group)

        self.set_group_id("default")

        self.connect('show', self.__show_cb)
        self.connect('hide', self.__hide_cb)
        self.connect('realize', self.__realize_cb)
        self.connect('destroy', self.__destroy_cb)
        self.connect('enter-notify-event', self.__enter_notify_event_cb)
        self.connect('leave-notify-event', self.__leave_notify_event_cb)

        self._mouse_detector = MouseSpeedDetector(self, 200, 5)
        self._mouse_detector.connect('motion-slow', self._mouse_slow_cb)

    def __destroy_cb(self, palette):
        self.set_group_id(None)

    def set_invoker(self, invoker):
        for hid in self._invoker_hids[:]:
            self._invoker.disconnect(hid)
            self._invoker_hids.remove(hid)

        self._invoker = invoker
        if invoker is not None:
            self._invoker_hids.append(self._invoker.connect(
                'mouse-enter', self._invoker_mouse_enter_cb))
            self._invoker_hids.append(self._invoker.connect(
                'mouse-leave', self._invoker_mouse_leave_cb))
            self._invoker_hids.append(self._invoker.connect(
                'right-click', self._invoker_right_click_cb))

    def get_invoker(self):
        return self._invoker

    invoker = gobject.property(type=object,
                               getter=get_invoker,
                               setter=set_invoker)

    def __realize_cb(self, widget):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)

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

    def set_group_id(self, group_id):
        if self._group_id:
            group = palettegroup.get_group(self._group_id)
            group.remove(self)
        if group_id:
            self._group_id = group_id
            group = palettegroup.get_group(group_id)
            group.add(self)

    def get_group_id(self):
        return self._group_id

    group_id = gobject.property(type=str,
                                getter=get_group_id,
                                setter=set_group_id)

    def do_size_request(self, requisition):
        gtk.Window.do_size_request(self, requisition)
        requisition.width = max(requisition.width, style.GRID_CELL_SIZE * 2)

    def do_size_allocate(self, allocation):
        gtk.Window.do_size_allocate(self, allocation)

        if self._old_alloc is None or \
           self._old_alloc.x != allocation.x or \
           self._old_alloc.y != allocation.y or \
           self._old_alloc.width != allocation.width or \
           self._old_alloc.height != allocation.height:
            self.queue_draw()

        # We need to store old allocation because when size_allocate
        # is called widget.allocation is already updated.
        # gtk.Window resizing is different from normal containers:
        # the X window is resized, widget.allocation is updated from
        # the configure request handler and finally size_allocate is called.
        self._old_alloc = allocation

    def do_expose_event(self, event):
        # We want to draw a border with a beautiful gap
        if self._invoker is not None and self._invoker.has_rectangle_gap():
            invoker = self._invoker.get_rect()
            palette = self.get_rect()

            gap = _calculate_gap(palette, invoker)
        else:
            gap = False

        allocation = self.get_allocation()
        wstyle = self.get_style()

        if gap:
            wstyle.paint_box_gap(event.window, gtk.STATE_PRELIGHT,
                                 gtk.SHADOW_IN, event.area, self, "palette",
                                 0, 0, allocation.width, allocation.height,
                                 gap[0], gap[1], gap[2])
        else:
            wstyle.paint_box(event.window, gtk.STATE_PRELIGHT,
                             gtk.SHADOW_IN, event.area, self, "palette",
                             0, 0, allocation.width, allocation.height)

        # Fall trough to the container expose handler.
        # (Leaving out the window expose handler which redraws everything)
        gtk.Bin.do_expose_event(self, event)

    def update_position(self):
        invoker = self._invoker
        if invoker is None or self._alignment is None:
            logging.error('Cannot update the palette position.')
            return

        rect = self.size_request()
        position = invoker.get_position_for_alignment(self._alignment, rect)
        if position is None:
            position = invoker.get_position(rect)

        self.move(position.x, position.y)

    def get_full_size_request(self):
        return self.size_request()

    def popup(self, immediate=False):
        if self._invoker is not None:
            full_size_request = self.get_full_size_request()
            self._alignment = self._invoker.get_alignment(full_size_request)

            self.update_position()
            self.set_transient_for(self._invoker.get_toplevel())

        self._popdown_anim.stop()

        if not immediate:
            self._popup_anim.start()
        else:
            self._popup_anim.stop()
            self.show()
            # we have to invoke update_position() twice
            # since WM could ignore first move() request
            self.update_position()

    def popdown(self, immediate=False):
        logging.debug('PaletteWindow.popdown immediate %r', immediate)

        self._popup_anim.stop()
        self._mouse_detector.stop()

        if not immediate:
            self._popdown_anim.start()
        else:
            self._popdown_anim.stop()
            self.size_request()
            self.hide()

    def on_invoker_enter(self):
        self._popdown_anim.stop()
        self._mouse_detector.start()

    def on_invoker_leave(self):
        self._mouse_detector.stop()
        self.popdown()

    def on_enter(self, event):
        self._popdown_anim.stop()

    def on_leave(self, event):
        self.popdown()

    def _invoker_mouse_enter_cb(self, invoker):
        self.on_invoker_enter()

    def _invoker_mouse_leave_cb(self, invoker):
        self.on_invoker_leave()

    def _invoker_right_click_cb(self, invoker):
        self.popup(immediate=True)

    def __enter_notify_event_cb(self, widget, event):
        if event.detail != gtk.gdk.NOTIFY_INFERIOR and \
                event.mode == gtk.gdk.CROSSING_NORMAL:
            self.on_enter(event)

    def __leave_notify_event_cb(self, widget, event):
        if event.detail != gtk.gdk.NOTIFY_INFERIOR and \
                event.mode == gtk.gdk.CROSSING_NORMAL:
            self.on_leave(event)

    def __show_cb(self, widget):
        if self._invoker is not None:
            self._invoker.notify_popup()

        self._up = True
        self.emit('popup')

    def __hide_cb(self, widget):
        logging.debug('__hide_cb')

        if self._invoker:
            self._invoker.notify_popdown()

        self._up = False
        self.emit('popdown')

    def get_rect(self):
        win_x, win_y = self.window.get_origin()
        rectangle = self.get_allocation()

        x = win_x + rectangle.x
        y = win_y + rectangle.y
        width, height = self.size_request()

        return gtk.gdk.Rectangle(x, y, width, height)

    def get_palette_state(self):
        return self._palette_state

    def _set_palette_state(self, state):
        self._palette_state = state

    def set_palette_state(self, state):
        self._set_palette_state(state)

    palette_state = property(get_palette_state)


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


class Invoker(gobject.GObject):

    __gtype_name__ = 'SugarPaletteInvoker'

    __gsignals__ = {
        'mouse-enter': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'mouse-leave': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'right-click': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'focus-out': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
    }

    ANCHORED = 0
    AT_CURSOR = 1

    BOTTOM = [(0.0, 0.0, 0.0, 1.0), (-1.0, 0.0, 1.0, 1.0)]
    RIGHT = [(0.0, 0.0, 1.0, 0.0), (0.0, -1.0, 1.0, 1.0)]
    TOP = [(0.0, -1.0, 0.0, 0.0), (-1.0, -1.0, 1.0, 0.0)]
    LEFT = [(-1.0, 0.0, 0.0, 0.0), (-1.0, -1.0, 0.0, 1.0)]

    def __init__(self):
        gobject.GObject.__init__(self)

        self.parent = None

        self._screen_area = gtk.gdk.Rectangle(0, 0, gtk.gdk.screen_width(),
                                              gtk.gdk.screen_height())
        self._position_hint = self.ANCHORED
        self._cursor_x = -1
        self._cursor_y = -1
        self._palette = None

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
            display = gtk.gdk.display_get_default()
            screen_, x, y, mask_ = display.get_pointer()
            self._cursor_x = x
            self._cursor_y = y

        if self._position_hint is self.ANCHORED:
            rect = self.get_rect()
        else:
            dist = style.PALETTE_CURSOR_DISTANCE
            rect = gtk.gdk.Rectangle(self._cursor_x - dist,
                                     self._cursor_y - dist,
                                     dist * 2, dist * 2)

        palette_width, palette_height = palette_dim

        x = rect.x + rect.width * invoker_halign + \
            palette_width * palette_halign

        y = rect.y + rect.height * invoker_valign + \
            palette_height * palette_valign

        return gtk.gdk.Rectangle(int(x), int(y),
                                 palette_width, palette_height)

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
                pv = -float(dtop) / palette_dim[1]

            # Set palette_valign to align to screen on the bottom
            else:
                pv = -float(palette_dim[1] - dbottom - rect.height) \
                        / palette_dim[1]

        elif best_alignment in self.TOP or best_alignment in self.BOTTOM:
            dleft = rect.x - screen_area.x
            dright = screen_area.x + screen_area.width - rect.x - rect.width

            ih = 0

            # Set palette_halign to align to screen on left
            if dleft > dright:
                ph = -float(dleft) / palette_dim[0]

            # Set palette_halign to align to screen on right
            else:
                ph = -float(palette_dim[0] - dright - rect.width) \
                        / palette_dim[0]

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

    def notify_right_click(self):
        self._ensure_palette_exists()
        self.emit('right-click')

    def get_palette(self):
        return self._palette

    def set_palette(self, palette):
        if self._palette is not None:
            self._palette.popdown(immediate=True)

        if self._palette:
            self._palette.props.invoker = None

        self._palette = palette

        if self._palette:
            self._palette.props.invoker = self

    palette = gobject.property(
        type=object, setter=set_palette, getter=get_palette)


class WidgetInvoker(Invoker):

    def __init__(self, parent=None, widget=None):
        Invoker.__init__(self)

        self._widget = None
        self._enter_hid = None
        self._leave_hid = None
        self._release_hid = None

        if parent or widget:
            self.attach_widget(parent, widget)

    def attach_widget(self, parent, widget=None):
        if widget:
            self._widget = widget
        else:
            self._widget = parent

        self.notify('widget')

        self._enter_hid = self._widget.connect('enter-notify-event',
            self.__enter_notify_event_cb)
        self._leave_hid = self._widget.connect('leave-notify-event',
            self.__leave_notify_event_cb)
        self._release_hid = self._widget.connect('button-release-event',
            self.__button_release_event_cb)

        self.attach(parent)

    def detach(self):
        Invoker.detach(self)
        self._widget.disconnect(self._enter_hid)
        self._widget.disconnect(self._leave_hid)
        self._widget.disconnect(self._release_hid)

    def get_rect(self):
        allocation = self._widget.get_allocation()
        if self._widget.window is not None:
            x, y = self._widget.window.get_origin()
        else:
            logging.warning(
                "Trying to position palette with invoker that's not realized.")
            x = 0
            y = 0

        if self._widget.flags() & gtk.NO_WINDOW:
            x += allocation.x
            y += allocation.y

        width = allocation.width
        height = allocation.height

        return gtk.gdk.Rectangle(x, y, width, height)

    def has_rectangle_gap(self):
        return True

    def draw_rectangle(self, event, palette):
        if self._widget.flags() & gtk.NO_WINDOW:
            x, y = self._widget.allocation.x, self._widget.allocation.y
        else:
            x = y = 0

        wstyle = self._widget.get_style()
        gap = _calculate_gap(self.get_rect(), palette.get_rect())

        if gap:
            wstyle.paint_box_gap(event.window, gtk.STATE_PRELIGHT,
                                 gtk.SHADOW_IN, event.area, self._widget,
                                 "palette-invoker", x, y,
                                 self._widget.allocation.width,
                                 self._widget.allocation.height,
                                 gap[0], gap[1], gap[2])
        else:
            wstyle.paint_box(event.window, gtk.STATE_PRELIGHT,
                             gtk.SHADOW_IN, event.area, self._widget,
                             "palette-invoker", x, y,
                             self._widget.allocation.width,
                             self._widget.allocation.height)

    def __enter_notify_event_cb(self, widget, event):
        self.notify_mouse_enter()

    def __leave_notify_event_cb(self, widget, event):
        self.notify_mouse_leave()

    def __button_release_event_cb(self, widget, event):
        if event.button == 3:
            self.notify_right_click()
            return True
        else:
            return False

    def get_toplevel(self):
        return self._widget.get_toplevel()

    def notify_popup(self):
        Invoker.notify_popup(self)
        self._widget.queue_draw()

    def notify_popdown(self):
        Invoker.notify_popdown(self)
        self._widget.queue_draw()

    def _get_widget(self):
        return self._widget
    widget = gobject.property(type=object, getter=_get_widget, setter=None)


class CanvasInvoker(Invoker):

    def __init__(self, parent=None):
        Invoker.__init__(self)

        self._position_hint = self.AT_CURSOR
        self._motion_hid = None
        self._release_hid = None
        self._item = None

        if parent:
            self.attach(parent)

    def attach(self, parent):
        Invoker.attach(self, parent)

        self._item = parent
        self._motion_hid = self._item.connect('motion-notify-event',
                                              self.__motion_notify_event_cb)
        self._release_hid = self._item.connect('button-release-event',
                                               self.__button_release_event_cb)

    def detach(self):
        Invoker.detach(self)
        self._item.disconnect(self._motion_hid)
        self._item.disconnect(self._release_hid)

    def get_default_position(self):
        return self.AT_CURSOR

    def get_rect(self):
        context = self._item.get_context()
        if context:
            x, y = context.translate_to_screen(self._item)
            width, height = self._item.get_allocation()
            return gtk.gdk.Rectangle(x, y, width, height)
        else:
            return gtk.gdk.Rectangle()

    def __motion_notify_event_cb(self, button, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            self.notify_mouse_enter()
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            self.notify_mouse_leave()

        return False

    def __button_release_event_cb(self, button, event):
        if event.button == 3:
            self.notify_right_click()
            return True
        else:
            return False

    def get_toplevel(self):
        return hippo.get_canvas_for_item(self._item).get_toplevel()


class ToolInvoker(WidgetInvoker):

    def __init__(self, parent=None):
        WidgetInvoker.__init__(self)

        if parent:
            self.attach_tool(parent)

    def attach_tool(self, widget):
        self.attach_widget(widget, widget.child)

    def _get_alignments(self):
        parent = self._widget.get_parent()
        if parent is None:
            return WidgetInvoker._get_alignments()

        if parent.get_orientation() is gtk.ORIENTATION_HORIZONTAL:
            return self.BOTTOM + self.TOP
        else:
            return self.LEFT + self.RIGHT


class CellRendererInvoker(Invoker):

    def __init__(self):
        Invoker.__init__(self)

        self._position_hint = self.AT_CURSOR
        self._tree_view = None
        self._cell_renderer = None
        self._motion_hid = None
        self._leave_hid = None
        self._release_hid = None
        self.path = None

    def attach_cell_renderer(self, tree_view, cell_renderer):
        self._tree_view = tree_view
        self._cell_renderer = cell_renderer

        self._motion_hid = tree_view.connect('motion-notify-event',
                                             self.__motion_notify_event_cb)
        self._leave_hid = tree_view.connect('leave-notify-event',
                                            self.__leave_notify_event_cb)
        self._release_hid = tree_view.connect('button-release-event',
                                              self.__button_release_event_cb)

        self.attach(cell_renderer)

    def detach(self):
        Invoker.detach(self)
        self._tree_view.disconnect(self._motion_hid)
        self._tree_view.disconnect(self._leave_hid)
        self._tree_view.disconnect(self._release_hid)

    def get_rect(self):
        allocation = self._tree_view.get_allocation()
        if self._tree_view.window is not None:
            x, y = self._tree_view.window.get_origin()
        else:
            logging.warning(
                "Trying to position palette with invoker that's not realized.")
            x = 0
            y = 0

        if self._tree_view.flags() & gtk.NO_WINDOW:
            x += allocation.x
            y += allocation.y

        width = allocation.width
        height = allocation.height

        return gtk.gdk.Rectangle(x, y, width, height)

    def __motion_notify_event_cb(self, widget, event):
        if event.window != widget.get_bin_window():
            return
        if self._point_in_cell_renderer(event.x, event.y):

            tree_view = self._tree_view
            path, column_, x_, y_ = tree_view.get_path_at_pos(int(event.x),
                                                              int(event.y))
            if path != self.path:
                if self.path is not None:
                    self._redraw_path(self.path)
                if path is not None:
                    self._redraw_path(path)
                if self.palette is not None:
                    self.palette.popdown(immediate=True)
                    self.palette = None
                self.path = path

            self.notify_mouse_enter()
        else:
            if self.path is not None:
                self._redraw_path(self.path)
            self.path = None
            self.notify_mouse_leave()

    def _redraw_path(self, path):
        for column in self._tree_view.get_columns():
            if self._cell_renderer in column.get_cell_renderers():
                break
        area = self._tree_view.get_background_area(path, column)
        x, y = \
            self._tree_view.convert_bin_window_to_widget_coords(area.x, area.y)
        self._tree_view.queue_draw_area(x, y, area.width, area.height)

    def __leave_notify_event_cb(self, widget, event):
        self.notify_mouse_leave()

    def __button_release_event_cb(self, widget, event):
        if event.button == 1 and self._point_in_cell_renderer(event.x,
            event.y):
            tree_view = self._tree_view
            path, column_, x_, y_ = tree_view.get_path_at_pos(int(event.x),
                                                              int(event.y))
            self._cell_renderer.emit('clicked', path)
            # So the treeview receives it and knows a drag isn't going on
            return False
        if event.button == 3 and self._point_in_cell_renderer(event.x,
            event.y):
            self.notify_right_click()
            return True
        else:
            return False

    def _point_in_cell_renderer(self, event_x, event_y):
        pos = self._tree_view.get_path_at_pos(int(event_x), int(event_y))
        if pos is None:
            return False

        path_, column, x, y_ = pos

        for cell_renderer in column.get_cell_renderers():
            if cell_renderer == self._cell_renderer:
                cell_x, cell_width = column.cell_get_position(cell_renderer)
                if x > cell_x and x < (cell_x + cell_width):
                    return True
                return False

        return False

    def get_toplevel(self):
        return self._tree_view.get_toplevel()

    def notify_popup(self):
        Invoker.notify_popup(self)

    def notify_popdown(self):
        Invoker.notify_popdown(self)
        self.palette = None

    def get_default_position(self):
        return self.AT_CURSOR

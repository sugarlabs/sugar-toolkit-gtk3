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

import gtk
import gobject
import logging
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE

from sugar.graphics import style
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.palette import _PopupAnimation, _PopdownAnimation
from sugar.graphics.palette import MouseSpeedDetector, Invoker
from sugar.graphics import animator
from sugar.graphics import palettegroup

ARROW_SIZE = hasattr(style, 'TOOLBAR_ARROW_SIZE') and style.TOOLBAR_ARROW_SIZE \
        or 8

class ToolbarButton(ToolButton):
    def __init__(self, **kwargs):
        self._page = None

        ToolButton.__init__(self, **kwargs)

        if self.palette is None:
            self.palette = _Palette(self)

        self.connect('clicked',
                lambda widget: self.set_expanded(not self.expanded))

    def get_toolbar(self):
        if not hasattr(self.parent, 'owner'):
            return None
        return self.parent.owner

    toolbar = property(get_toolbar)

    def get_page(self):
        return self._page.child.child

    def set_page(self, page):
        self._page = _align(_Box, page)
        self._page._toolitem = self
        page.show()

    page = gobject.property(type=object, getter=get_page, setter=set_page)

    def get_expanded(self):
        return bool(self.toolbar) and bool(self._page) and \
                self.toolbar._expanded_page() == self._page

    def set_expanded(self, value):
        if not self.toolbar or not self._page or self.get_expanded() == value:
            return

        if isinstance(self.palette, _Palette) and self.palette.is_up():
            self.palette.popdown(immediate=True)

        if not value:
            self.toolbar._shrink_page(self._page)
            return

        expanded = self.toolbar._expanded_page()
        if expanded and expanded._toolitem.window:
            expanded._toolitem.window.invalidate_rect(None, True)

        if self._page.parent:
            self.palette.remove(self._page)

        self.modify_bg(gtk.STATE_NORMAL, self.toolbar._bg)

        self.toolbar._expand_page(self._page)

    expanded = property(get_expanded, set_expanded)

    def do_expose_event(self, event):
        if not self.expanded or self.palette and self.palette.is_up():
            ToolButton.do_expose_event(self, event)
            if self.palette and self.palette.is_up():
                _paint_arrow(self, event, gtk.ARROW_DOWN)
            else:
                _paint_arrow(self, event, gtk.ARROW_UP)
            return

        alloc = self.allocation

        self.get_style().paint_box(event.window,
                gtk.STATE_NORMAL, gtk.SHADOW_IN, event.area, self,
                'palette-invoker', alloc.x, 0,
                alloc.width, alloc.height + style._FOCUS_LINE_WIDTH)

        if self.child.state != gtk.STATE_PRELIGHT:
            self.get_style().paint_box(event.window,
                    gtk.STATE_NORMAL, gtk.SHADOW_NONE, event.area, self, None,
                    alloc.x + style._FOCUS_LINE_WIDTH, style._FOCUS_LINE_WIDTH,
                    alloc.width - style._FOCUS_LINE_WIDTH*2, alloc.height)

        gtk.ToolButton.do_expose_event(self, event)
        _paint_arrow(self, event, gtk.ARROW_DOWN)

class Toolbar(gtk.VBox):
    def __init__(self, padding=style.TOOLBOX_HORIZONTAL_PADDING):
        gtk.VBox.__init__(self)

        self.__top = gtk.Toolbar()
        self.__top.owner = self

        top_widget = _align(gtk.EventBox, self.__top)
        self.pack_start(top_widget)

        self.props.padding = padding
        self.modify_bg(gtk.STATE_NORMAL,
                style.COLOR_TOOLBAR_GREY.get_gdk_color())

        self.__notebook = gtk.Notebook()
        self.__notebook.set_show_border(False)
        self.__notebook.set_show_tabs(False)
        self.__notebook.show()

        self.__top.connect('remove', self.__remove_cb)

    top = property(lambda self: self.__top)

    def get_padding(self):
        return self.__top.parent.props.left_padding

    def set_padding(self, pad):
        self.__top.parent.set_padding(0, 0, pad, pad)

    padding = gobject.property(type=object,
            getter=get_padding, setter=set_padding)

    def get_subs(self):
        out = []
        for i in range(self.top.get_n_items()):
            page = self.top.get_nth_item(i)
            if isinstance(page, ToolbarButton):
                out.append(page)
        return out

    subs = property(get_subs)

    def modify_bg(self, state, color):
        if state == gtk.STATE_NORMAL:
            self._bg = color
        self.__top.parent.parent.modify_bg(state, color)
        self.__top.modify_bg(state, color)

    def __remove_cb(self, sender, widget):
        if not isinstance(widget, ToolbarButton):
            return
        page_no = self.__notebook.page_num(widget._page)
        if page_no != -1:
            self.__notebook.remove_page(page_no)
        if widget.palette:
            widget.palette.popdown(immediate=True)

    def _expanded_page(self):
        if self.__notebook.parent is None:
            return None
        page_no = self.__notebook.get_current_page()
        return self.__notebook.get_nth_page(page_no)

    def _shrink_page(self, page):
        page_no = self.__notebook.page_num(page)
        if page_no == -1:
            return
        self.__notebook.remove_page(page_no)
        self.remove(self.__notebook)

    def _expand_page(self, page):
        for i in range(self.__notebook.get_n_pages()):
            self.__notebook.remove_page(0)

        _setup_page(page, self._bg, self.props.padding)
        self.__notebook.append_page(page)

        if self.__notebook.parent is None:
            self.pack_start(self.__notebook)

class _Box(gtk.EventBox):
    def __init__(self):
        gtk.EventBox.__init__(self)
        self.connect('expose-event', self.do_expose_event)
        self.set_app_paintable(True)

    def do_expose_event(self, widget, event):
        a = self._toolitem.allocation
        self.get_style().paint_box(event.window,
                gtk.STATE_NORMAL, gtk.SHADOW_IN, event.area, self,
                'palette-invoker', -style._FOCUS_LINE_WIDTH, 0,
                self.allocation.width + style._FOCUS_LINE_WIDTH*2,
                self.allocation.height + style._FOCUS_LINE_WIDTH)
        self.get_style().paint_box(event.window,
                gtk.STATE_NORMAL, gtk.SHADOW_NONE, event.area, self, None,
                a.x + style._FOCUS_LINE_WIDTH, 0,
                a.width - style._FOCUS_LINE_WIDTH*2, style._FOCUS_LINE_WIDTH)

class _Palette(gtk.Window):
    def __init__(self, toolitem, **kwargs):
        gobject.GObject.__init__(self, **kwargs)

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_border_width(0)

        self._toolitem = toolitem
        self._invoker = None
        self._up = False
        self._invoker_hids = []
        self.__focus = 0

        self._popup_anim = animator.Animator(.5, 10)
        self._popup_anim.add(_PopupAnimation(self))

        self._popdown_anim = animator.Animator(0.6, 10)
        self._popdown_anim.add(_PopdownAnimation(self))

        accel_group = gtk.AccelGroup()
        self.set_data('sugar-accel-group', accel_group)
        self.add_accel_group(accel_group)

        self.connect('show', self.__show_cb)
        self.connect('hide', self.__hide_cb)
        self.connect('realize', self.__realize_cb)
        self.connect('enter-notify-event', self.__enter_notify_event_cb)
        self.connect('leave-notify-event', self.__leave_notify_event_cb)

        self._mouse_detector = MouseSpeedDetector(self, 200, 5)
        self._mouse_detector.connect('motion-slow', self._mouse_slow_cb)

        group = palettegroup.get_group('default')
        group.connect('popdown', self.__group_popdown_cb)

    def is_up(self):
        return self._up

    def get_rect(self):
        win_x, win_y = self.window.get_origin()
        rectangle = self.get_allocation()

        x = win_x + rectangle.x
        y = win_y + rectangle.y
        width = rectangle.width
        height = rectangle.height

        return gtk.gdk.Rectangle(x, y, width, height)

    def set_invoker(self, invoker):
        for hid in self._invoker_hids[:]:
            self._invoker.disconnect(hid)
            self._invoker_hids.remove(hid)

        self._invoker = invoker
        if invoker is not None:
            self._invoker_hids.append(self._invoker.connect(
                'mouse-enter', self.__invoker_mouse_enter_cb))
            self._invoker_hids.append(self._invoker.connect(
                'mouse-leave', self.__invoker_mouse_leave_cb))
            self._invoker_hids.append(self._invoker.connect(
                'right-click', self.__invoker_right_click_cb))

    def get_invoker(self):
        return self._invoker

    invoker = gobject.property(type=object,
                               getter=get_invoker,
                               setter=set_invoker)

    def do_size_request(self, requisition):
        gtk.Window.do_size_request(self, requisition)
        if self._toolitem.toolbar:
            requisition.width = self._toolitem.toolbar.allocation.width

    def __realize_cb(self, widget):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        #accept_focus = len(self._content.get_children())
        #if self.window:
        #    self.window.set_accept_focus(accept_focus)

    def popup(self, immediate=False):
        self._popdown_anim.stop()

        toolbar = self._toolitem.toolbar
        page = self._toolitem._page

        if not self._invoker or self._toolitem.expanded or not toolbar:
            return

        _setup_page(page, style.COLOR_BLACK.get_gdk_color(),
                toolbar.props.padding)
        if self.child is None:
            self.add(page)

        x, y = toolbar.window.get_origin()
        self.move(x + toolbar.allocation.x, y + toolbar.top.allocation.height)
        self.set_transient_for(self._invoker.get_toplevel())

        if not immediate:
            self._popup_anim.start()
        else:
            self.show()

    def popdown(self, immediate=False):
        self._popup_anim.stop()
        self._mouse_detector.stop()

        if not immediate:
            self._popdown_anim.start()
        else:
            self.hide()

    def _mouse_slow_cb(self, widget):
        self._mouse_detector.stop()

        if self.is_up():
            self._popdown_anim.stop()
            return

        self.popup(immediate=False)

    def __handle_focus(self, delta):
        self.__focus += delta
        if self.__focus not in (0, 1):
            logging.error('_Palette.__focus=%s not in (0, 1)' % self.__focus)

        if self.__focus == 0:
            group = palettegroup.get_group('default')
            if not group.is_up():
                self.popdown()

    def __group_popdown_cb(self, group):
        if self.__focus == 0:
            self.popdown(immediate=True)

    def __invoker_mouse_enter_cb(self, invoker):
        self._mouse_detector.start()
        self.__handle_focus(+1)

    def __invoker_mouse_leave_cb(self, invoker):
        self._mouse_detector.stop()
        self.__handle_focus(-1)

    def __invoker_right_click_cb(self, invoker):
        self.popup(immediate=True)

    def __enter_notify_event_cb(self, widget, event):
        if event.detail != gtk.gdk.NOTIFY_INFERIOR and \
                event.mode == gtk.gdk.CROSSING_NORMAL:
            self._popdown_anim.stop()
            self.__handle_focus(+1)

    def __leave_notify_event_cb(self, widget, event):
        if event.detail != gtk.gdk.NOTIFY_INFERIOR and \
                event.mode == gtk.gdk.CROSSING_NORMAL:
            self.__handle_focus(-1)

    def __show_cb(self, widget):
        self._invoker.notify_popup()
        self._up = True

    def __hide_cb(self, widget):
        if self._invoker:
            self._invoker.notify_popdown()
        self._up = False

def _setup_page(page, color, hpad):
    vpad = style._FOCUS_LINE_WIDTH
    page.child.set_padding(vpad, vpad, hpad, hpad)
    page.child.child.modify_bg(gtk.STATE_NORMAL, color)
    page.modify_bg(gtk.STATE_NORMAL, color)
    page.modify_bg(gtk.STATE_PRELIGHT, color)

def _align(box_class, widget):
    widget.show()
    alignment = gtk.Alignment(0.0, 0.0, 1.0, 1.0)
    alignment.add(widget)
    alignment.show()
    box = box_class()
    box.modify_bg(gtk.STATE_ACTIVE, style.COLOR_BUTTON_GREY.get_gdk_color())
    box.add(alignment)
    box.show()
    return box

def _paint_arrow(widget, event, type):
    a = widget.allocation
    widget.get_style().paint_arrow(event.window,
            gtk.STATE_NORMAL, gtk.SHADOW_IN, event.area, widget,
            None, type,  True,
            a.x + a.width/2 - ARROW_SIZE/2,
            a.y + a.height - ARROW_SIZE - style._FOCUS_LINE_WIDTH,
            ARROW_SIZE, ARROW_SIZE)

# Copyright (C) 2009, Aleksey Lim
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

import gtk
import gobject
import logging

from sugar.graphics import style
from sugar.graphics.palette import PaletteWindow, ToolInvoker
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics import palettegroup


class ToolbarButton(ToolButton):

    def __init__(self, page=None, **kwargs):
        ToolButton.__init__(self, **kwargs)

        self.page_widget = None

        self.set_page(page)

        self.connect('clicked',
                lambda widget: self.set_expanded(not self.is_expanded()))

    def get_toolbar_box(self):
        if not hasattr(self.parent, 'owner'):
            return None
        return self.parent.owner

    toolbar_box = property(get_toolbar_box)

    def get_page(self):
        if self.page_widget is None:
            return None
        return self.page_widget.child.child

    def set_page(self, page):
        if page is None:
            self.page_widget = None
            return
        self.page_widget = _embody_page(_Box, page)
        self.page_widget.set_size_request(-1, style.GRID_CELL_SIZE)
        self.page_widget.toolbar_button = self
        page.show()
        if self.props.palette is None:
            self.props.palette = _ToolbarPalette(invoker=ToolInvoker(self))
            self.props.palette.toolbar_button = self
        self._move_page_to_palette()

    page = gobject.property(type=object, getter=get_page, setter=set_page)

    def _move_page_to_palette(self):
        if self.page_widget is None:
            return

        if self.toolbar_box is not None and \
                self.page_widget in self.toolbar_box.get_children():
            self.toolbar_box.remove(self.page_widget)

        if isinstance(self.props.palette, _ToolbarPalette):
            self.props.palette.add(self.page_widget)

    def is_expanded(self):
        return self.toolbar_box is not None and self.page_widget is not None \
                and self.toolbar_box.expanded_button == self

    def popdown(self):
        if self.props.palette is not None:
            self.props.palette.popdown(immediate=True)

    def set_expanded(self, expanded):
        self.popdown()

        box = self.toolbar_box

        if box is None or self.page_widget is None or \
                self.is_expanded() == expanded:
            return

        if not expanded:
            box.remove(self.page_widget)
            box.expanded_button = None
            self._move_page_to_palette()
            return

        if box.expanded_button is not None:
            # need to redraw it to erase arrow
            expanded_toolitem = box.expanded_button.page_widget.toolbar_button
            if expanded_toolitem.window is not None:
                expanded_toolitem.window.invalidate_rect(None, True)
            box.expanded_button.set_expanded(False)

        if self.page_widget.parent is not None:
            self.props.palette.remove(self.page_widget)

        self.modify_bg(gtk.STATE_NORMAL, box.background)
        _setup_page(self.page_widget, box.background, box.props.padding)
        box.pack_start(self.page_widget)
        box.expanded_button = self

    def do_expose_event(self, event):
        if not self.is_expanded() or self.props.palette is not None and \
                self.props.palette.is_up():
            ToolButton.do_expose_event(self, event)
            _paint_arrow(self, event, gtk.ARROW_DOWN)
            return

        alloc = self.allocation

        self.get_style().paint_box(event.window,
                gtk.STATE_NORMAL, gtk.SHADOW_IN, event.area, self,
                'palette-invoker', alloc.x, 0,
                alloc.width, alloc.height + style.FOCUS_LINE_WIDTH)

        if self.child.state != gtk.STATE_PRELIGHT:
            self.get_style().paint_box(event.window,
                    gtk.STATE_NORMAL, gtk.SHADOW_NONE, event.area, self, None,
                    alloc.x + style.FOCUS_LINE_WIDTH, style.FOCUS_LINE_WIDTH,
                    alloc.width - style.FOCUS_LINE_WIDTH * 2, alloc.height)

        gtk.ToolButton.do_expose_event(self, event)
        _paint_arrow(self, event, gtk.ARROW_UP)


class ToolbarBox(gtk.VBox):

    def __init__(self, padding=style.TOOLBOX_HORIZONTAL_PADDING):
        gtk.VBox.__init__(self)
        self.expanded_button = None
        self.background = None

        self._toolbar = gtk.Toolbar()
        self._toolbar.owner = self
        self._toolbar.connect('remove', self.__remove_cb)

        top_widget = _embody_page(gtk.EventBox, self._toolbar)
        self.pack_start(top_widget)

        self.props.padding = padding
        self.modify_bg(gtk.STATE_NORMAL,
                style.COLOR_TOOLBAR_GREY.get_gdk_color())

    def __remove_cb(self, sender, button):
        if not isinstance(button, ToolbarButton):
            return
        button.popdown()
        if self.expanded_button == button:
            self.remove(button.page_widget)
            self.expanded_button = None

    def get_toolbar(self):
        return self._toolbar

    toolbar = property(get_toolbar)

    def get_padding(self):
        return self.toolbar.parent.props.left_padding

    def set_padding(self, pad):
        self.toolbar.parent.set_padding(0, 0, pad, pad)

    padding = gobject.property(type=object,
            getter=get_padding, setter=set_padding)

    def modify_bg(self, state, color):
        if state == gtk.STATE_NORMAL:
            self.background = color
        self.toolbar.parent.parent.modify_bg(state, color)
        self.toolbar.modify_bg(state, color)


class _ToolbarPalette(PaletteWindow):

    def __init__(self, **kwargs):
        PaletteWindow.__init__(self, **kwargs)
        self.toolbar_box = None
        self.set_border_width(0)
        self._has_focus = False

        group = palettegroup.get_group('default')
        group.connect('popdown', self.__group_popdown_cb)
        self.set_group_id('toolbar_box')

    def on_invoker_enter(self):
        PaletteWindow.on_invoker_enter(self)
        self._set_focus(True)

    def on_invoker_leave(self):
        PaletteWindow.on_invoker_leave(self)
        self._set_focus(False)

    def on_enter(self, event):
        PaletteWindow.on_enter(self, event)
        self._set_focus(True)

    def on_leave(self, event):
        PaletteWindow.on_enter(self, event)
        self._set_focus(False)

    def _set_focus(self, new_focus):
        self._has_focus = new_focus
        if not self._has_focus:
            group = palettegroup.get_group('default')
            if not group.is_up():
                self.popdown()

    def do_size_request(self, requisition):
        gtk.Window.do_size_request(self, requisition)
        requisition.width = max(requisition.width,
                                gtk.gdk.screen_width())

    def popup(self, immediate=False):
        button = self.toolbar_button
        if button.is_expanded():
            return
        box = button.toolbar_box
        _setup_page(button.page_widget, style.COLOR_BLACK.get_gdk_color(),
                box.props.padding)
        PaletteWindow.popup(self, immediate)

    def __group_popdown_cb(self, group):
        if not self._has_focus:
            self.popdown(immediate=True)


class _Box(gtk.EventBox):

    def __init__(self):
        gtk.EventBox.__init__(self)
        self.connect('expose-event', self.do_expose_event)
        self.set_app_paintable(True)

    def do_expose_event(self, widget, event):
        alloc = self.toolbar_button.allocation
        self.get_style().paint_box(event.window,
                gtk.STATE_NORMAL, gtk.SHADOW_IN, event.area, self,
                'palette-invoker', -style.FOCUS_LINE_WIDTH, 0,
                self.allocation.width + style.FOCUS_LINE_WIDTH * 2,
                self.allocation.height + style.FOCUS_LINE_WIDTH)
        self.get_style().paint_box(event.window,
                gtk.STATE_NORMAL, gtk.SHADOW_NONE, event.area, self, None,
                alloc.x + style.FOCUS_LINE_WIDTH, 0,
                alloc.width - style.FOCUS_LINE_WIDTH * 2,
                    style.FOCUS_LINE_WIDTH)


def _setup_page(page_widget, color, hpad):
    vpad = style.FOCUS_LINE_WIDTH
    page_widget.child.set_padding(vpad, vpad, hpad, hpad)

    page = page_widget.child.child
    page.modify_bg(gtk.STATE_NORMAL, color)
    if isinstance(page, gtk.Container):
        for i in page.get_children():
            i.modify_bg(gtk.STATE_INSENSITIVE, color)

    page_widget.modify_bg(gtk.STATE_NORMAL, color)
    page_widget.modify_bg(gtk.STATE_PRELIGHT, color)


def _embody_page(box_class, widget):
    widget.show()
    alignment = gtk.Alignment(0.0, 0.0, 1.0, 1.0)
    alignment.add(widget)
    alignment.show()
    box = box_class()
    box.modify_bg(gtk.STATE_ACTIVE, style.COLOR_BUTTON_GREY.get_gdk_color())
    box.add(alignment)
    box.show()
    return box


def _paint_arrow(widget, event, arrow_type):
    alloc = widget.allocation
    x = alloc.x + alloc.width / 2 - style.TOOLBAR_ARROW_SIZE / 2
    y = alloc.y + alloc.height - int(style.TOOLBAR_ARROW_SIZE * .85)

    widget.get_style().paint_arrow(event.window,
            gtk.STATE_NORMAL, gtk.SHADOW_NONE, event.area, widget,
            None, arrow_type, True,
            x, y, style.TOOLBAR_ARROW_SIZE, style.TOOLBAR_ARROW_SIZE)

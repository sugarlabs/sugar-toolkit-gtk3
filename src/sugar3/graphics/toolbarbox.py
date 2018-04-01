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

import math

from gi.repository import Gtk
from gi.repository import GObject

from sugar3.graphics import style
from sugar3.graphics.palettewindow import PaletteWindow, ToolInvoker, \
    _PaletteWindowWidget
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics import palettegroup


class ToolbarButton(ToolButton):

    def __init__(self, page=None, **kwargs):
        ToolButton.__init__(self, **kwargs)

        self.page_widget = None

        self.set_page(page)

        self.connect('clicked',
                     lambda widget: self.set_expanded(not self.is_expanded()))
        self.connect_after('draw', self.__drawing_cb)
        self.connect('hierarchy-changed', self.__hierarchy_changed_cb)

    def __hierarchy_changed_cb(self, tool_button, previous_toplevel):
        parent = self.get_parent()
        if hasattr(parent, 'owner'):
            if self.page_widget and previous_toplevel is None:
                self._unparent()
                parent.owner.pack_start(self.page_widget, True, True, 0)
                self.set_expanded(False)

    def get_toolbar_box(self):
        parent = self.get_parent()
        if not hasattr(parent, 'owner'):
            return None
        return parent.owner

    toolbar_box = property(get_toolbar_box)

    def get_page(self):
        if self.page_widget is None:
            return None
        return _get_embedded_page(self.page_widget)

    def set_page(self, page):
        if page is None:
            self.page_widget = None
            return
        self.page_widget, alignment_ = _embed_page(_Box(self), page)
        self.page_widget.set_size_request(-1, style.GRID_CELL_SIZE)
        page.show()
        if self.props.palette is None:
            self.props.palette = _ToolbarPalette(invoker=ToolInvoker(self))
        self._move_page_to_palette()

    page = GObject.Property(type=object, getter=get_page, setter=set_page)

    def is_in_palette(self):
        return self.page is not None and \
            self.page_widget.get_parent() == self.props.palette._widget

    def is_expanded(self):
        return self.page is not None and \
            not self.is_in_palette()

    def popdown(self):
        if self.props.palette is not None:
            self.props.palette.popdown(immediate=True)

    def set_expanded(self, expanded):
        self.popdown()
        palettegroup.popdown_all()

        if self.page is None or self.is_expanded() == expanded:
            return

        if not expanded:
            self._move_page_to_palette()
            return

        box = self.toolbar_box

        if box.expanded_button is not None:
            box.expanded_button.queue_draw()
            box.expanded_button.set_expanded(False)
        box.expanded_button = self

        self._unparent()

        self.modify_bg(Gtk.StateType.NORMAL, box.background)
        _setup_page(self.page_widget, box.background, box.props.padding)
        box.pack_start(self.page_widget, True, True, 0)

    def _move_page_to_palette(self):
        if self.is_in_palette():
            return

        self._unparent()

        if isinstance(self.props.palette, _ToolbarPalette):
            self.props.palette._widget.add(self.page_widget)

    def _unparent(self):
        page_parent = self.page_widget.get_parent()
        if page_parent is None:
            return
        page_parent.remove(self.page_widget)

    def __drawing_cb(self, button, cr):
        alloc = self.get_allocation()
        context = self.get_style_context()
        context.add_class('toolitem')
        context.add_class('toolbar-down')
        if not self.is_expanded() or self.props.palette is not None and \
                self.props.palette.is_up():
            ToolButton.do_draw(self, cr)
            _paint_arrow(self, cr, math.pi)
            return False
        Gtk.render_frame_gap(context, cr, 0, 0, alloc.width, alloc.height,
                             Gtk.PositionType.BOTTOM, 0, alloc.width)
        _paint_arrow(self, cr, 0)
        return False


class ToolbarBox(Gtk.VBox):

    __gtype_name__ = 'SugarToolbarBox'

    def __init__(self, padding=style.TOOLBOX_HORIZONTAL_PADDING):
        GObject.GObject.__init__(self)
        self._expanded_button_index = -1
        self.background = None

        self._toolbar = Gtk.Toolbar()
        self._toolbar.owner = self
        self._toolbar.connect('remove', self.__remove_cb)

        self._toolbar_widget, self._toolbar_alignment = \
            _embed_page(Gtk.EventBox(), self._toolbar)
        self.pack_start(self._toolbar_widget, True, True, 0)

        self.props.padding = padding
        self.modify_bg(Gtk.StateType.NORMAL,
                       style.COLOR_TOOLBAR_GREY.get_gdk_color())

    def get_toolbar(self):
        return self._toolbar

    toolbar = property(get_toolbar)

    def get_expanded_button(self):
        if self._expanded_button_index == -1:
            return None
        return self.toolbar.get_nth_item(self._expanded_button_index)

    def set_expanded_button(self, button):
        if button not in self.toolbar:
            self._expanded_button_index = -1
            return
        self._expanded_button_index = self.toolbar.get_item_index(button)

    expanded_button = property(get_expanded_button, set_expanded_button)

    def get_padding(self):
        return self._toolbar_alignment.props.left_padding

    def set_padding(self, pad):
        self._toolbar_alignment.set_padding(0, 0, pad, pad)

    padding = GObject.Property(type=object,
                               getter=get_padding, setter=set_padding)

    def modify_bg(self, state, color):
        if state == Gtk.StateType.NORMAL:
            self.background = color
        self._toolbar_widget.modify_bg(state, color)
        self.toolbar.modify_bg(state, color)

    def __remove_cb(self, sender, button):
        if not isinstance(button, ToolbarButton):
            return
        button.popdown()
        if button == self.expanded_button:
            self.remove(button.page_widget)
            self._expanded_button_index = -1


if hasattr(ToolbarBox, 'set_css_name'):
    ToolbarBox.set_css_name('toolbarbox')


class _ToolbarPalette(PaletteWindow):

    def __init__(self, **kwargs):
        PaletteWindow.__init__(self, **kwargs)
        self._has_focus = False

        group = palettegroup.get_group('default')
        group.connect('popdown', self.__group_popdown_cb)
        self.set_group_id('toolbarbox')

        self._widget = _PaletteWindowWidget()
        self._widget.set_border_width(0)
        self._setup_widget()

        self._widget.connect('realize', self._realize_cb)

    def get_expanded_button(self):
        return self.invoker.parent

    expanded_button = property(get_expanded_button)

    def on_invoker_enter(self):
        PaletteWindow.on_invoker_enter(self)
        self._set_focus(True)

    def on_invoker_leave(self):
        PaletteWindow.on_invoker_leave(self)
        self._set_focus(False)

    def on_enter(self):
        PaletteWindow.on_enter(self)
        self._set_focus(True)

    def on_leave(self):
        PaletteWindow.on_enter(self)
        self._set_focus(False)

    def _set_focus(self, new_focus):
        self._has_focus = new_focus
        if not self._has_focus:
            group = palettegroup.get_group('default')
            if not group.is_up():
                self.popdown()

    def _realize_cb(self, widget):
        screen = self._widget.get_screen()
        width = screen.width()
        self._widget.set_size_request(width, -1)

    def popup(self, immediate=False):
        button = self.expanded_button
        if button.is_expanded():
            return
        box = button.toolbar_box
        _setup_page(button.page_widget, style.COLOR_BLACK.get_gdk_color(),
                    box.props.padding)
        PaletteWindow.popup(self, immediate)

    def __group_popdown_cb(self, group):
        if not self._has_focus:
            self.popdown(immediate=True)


class _Box(Gtk.EventBox):

    def __init__(self, toolbar_button):
        GObject.GObject.__init__(self)
        self._toolbar_button = toolbar_button

    def do_draw(self, cr):
        self.get_child().do_draw(self, cr)

        button_alloc = self._toolbar_button.get_allocation()

        cr.set_line_width(style.FOCUS_LINE_WIDTH * 2)
        cr.set_source_rgba(*style.COLOR_BUTTON_GREY.get_rgba())
        cr.move_to(0, 0)
        cr.line_to(button_alloc.x + style.FOCUS_LINE_WIDTH, 0)
        cr.move_to(
            button_alloc.x + button_alloc.width - style.FOCUS_LINE_WIDTH, 0)
        cr.line_to(self.get_allocation().width, 0)
        cr.stroke()


def _setup_page(page_widget, color, hpad):
    page_widget.get_child().set_padding(0, 0, hpad, hpad)

    page = _get_embedded_page(page_widget)
    page.modify_bg(Gtk.StateType.NORMAL, color)
    if isinstance(page, Gtk.Container):
        for i in page.get_children():
            i.modify_bg(Gtk.StateType.INSENSITIVE, color)

    page_widget.modify_bg(Gtk.StateType.NORMAL, color)
    page_widget.modify_bg(Gtk.StateType.PRELIGHT, color)


def _embed_page(page_widget, page):
    page.show()

    alignment = Gtk.Alignment(xscale=1.0, yscale=1.0)
    alignment.add(page)
    alignment.show()

    page_widget.modify_bg(Gtk.StateType.ACTIVE,
                          style.COLOR_BUTTON_GREY.get_gdk_color())
    page_widget.add(alignment)
    page_widget.show()

    return (page_widget, alignment)


def _get_embedded_page(page_widget):
    return page_widget.get_child().get_child()


def _paint_arrow(widget, cr, angle):
    alloc = widget.get_allocation()

    arrow_size = style.TOOLBAR_ARROW_SIZE / 2
    y = alloc.height - arrow_size
    x = (alloc.width - arrow_size) / 2

    context = widget.get_style_context()
    context.add_class('toolitem')

    Gtk.render_arrow(context, cr, angle, x, y, arrow_size)

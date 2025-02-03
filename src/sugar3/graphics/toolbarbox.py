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
        self._last_parent = None  # track previous parent


        self.set_page(page)

        self.connect('clicked',
                     lambda widget: self.set_expanded(not self.is_expanded()))
        # self.connect_after('draw', self.__drawing_cb)
        self.connect('notify::parent', self.__hierarchy_changed_cb)

    def __hierarchy_changed_cb(self, tool_button, previous_toplevel):
        new_parent = self.get_parent()
        if self._last_parent is None and new_parent is not None and \
           hasattr(new_parent, 'owner') and self.page_widget:
            self._unparent()
            new_parent.owner.append(self.page_widget)
            self.set_expanded(False)
        self._last_parent = new_parent

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

        self.override_background_color(Gtk.StateFlags.NORMAL, box.background)
        _setup_page(self.page_widget, box.background, box.props.padding)
        box.append(self.page_widget)

    def _move_page_to_palette(self):
        if self.is_in_palette():
            return

        self._unparent()

        if isinstance(self.props.palette, _ToolbarPalette):
            self.props.palette._widget.set_child(self.page_widget)
            
    def _unparent(self):
        if self.page_widget.get_parent() is not None:
            self.page_widget.unparent()
            

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
    def do_snapshot(self, snapshot):
        # Add default style classes for consistency.
        self.get_style_context().add_class('toolitem')
        self.get_style_context().add_class('toolbar-down')

        # TODO: Implement custom arrow drawing using GTK4 snapshot APIs, if desired.
        # For now, defer to the parent's snapshot handling.
        return super().do_snapshot(snapshot)
class ToolbarBox(Gtk.Box):

    __gtype_name__ = 'SugarToolbarBox'

    def __init__(self, padding=style.TOOLBOX_HORIZONTAL_PADDING):
        GObject.GObject.__init__(self)
        self._expanded_button_index = -1
        self.background = None

        self._toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._toolbar.owner = self

        self._toolbar_widget, self._toolbar_alignment = \
            _embed_page(Gtk.Box(), self._toolbar)
        self.append(self._toolbar_widget)

        self.props.padding = padding
        self.override_background_color(Gtk.StateFlags.NORMAL,
                                       style.COLOR_TOOLBAR_GREY)

    def get_toolbar(self):
        return self._toolbar

    toolbar = property(get_toolbar)

    def get_expanded_button(self):
        if self._expanded_button_index == -1:
            return None
        return self.toolbar.get_child_at_index(self._expanded_button_index)

    def set_expanded_button(self, button):
        if button not in self.toolbar.get_children():
            self._expanded_button_index = -1
            return
        self._expanded_button_index = self.toolbar.get_children().index(button)

    expanded_button = property(get_expanded_button, set_expanded_button)

    def get_padding(self):
        return self._toolbar_alignment.get_margin_start()

    def set_padding(self, pad):
        self._toolbar_alignment.set_margin_start(pad)
        self._toolbar_alignment.set_margin_end(pad)

    padding = GObject.Property(type=int,
                               getter=get_padding, setter=set_padding)

    def override_background_color(self, state, color):
        if state == Gtk.StateFlags.NORMAL:
            self.background = color
        _override_background_color(self._toolbar_widget, state, color)
        _override_background_color(self.toolbar, state, color)

    def remove_button(self, button):
        if not isinstance(button, ToolbarButton):
            return
        button.popdown()
        if button == self.expanded_button:
            self.remove(button.page_widget)
            self._expanded_button_index = -1

    def remove(self, widget):
        self.remove_button(widget)
        super().remove(widget)


if hasattr(ToolbarBox, 'set_css_name'):
    ToolbarBox.set_css_name('toolbarbox')


class _ToolbarPalette(PaletteWindow):

    def __init__(self, **kwargs):
        PaletteWindow.__init__(self, **kwargs)
        self._has_focus = False

        group = palettegroup.get_group('default')
        group.connect('popdown', self.__group_popdown_cb)
        self.set_group_id('toolbarbox')

        self._widget = _PaletteWindowWidget(self)
        # self._widget.set_border_width(0)
        self._widget.set_margin_top(0)
        self._widget.set_margin_bottom(0)
        self._widget.set_margin_start(0)
        self._widget.set_margin_end(0)
        
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
        _setup_page(button.page_widget, style.COLOR_BLACK, box.props.padding)
        PaletteWindow.popup(self, immediate)

    def __group_popdown_cb(self, group):
        if not self._has_focus:
            self.popdown(immediate=True)


class _Box(Gtk.Box):

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
    page_widget.get_child().set_margin_start(hpad)
    page_widget.get_child().set_margin_end(hpad)

    page = _get_embedded_page(page_widget)
    _override_background_color(page, Gtk.StateFlags.NORMAL, color)
    if isinstance(page, Gtk.Container):
        for i in page.get_children():
            _override_background_color(i, Gtk.StateFlags.INSENSITIVE, color)

    _override_background_color(page_widget, Gtk.StateFlags.NORMAL, color)
    _override_background_color(page_widget, Gtk.StateFlags.PRELIGHT, color)


def _embed_page(page_widget, page):
    page.show()

    alignment = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    alignment.append(page)
    alignment.set_visible(True)

    _override_background_color(page_widget, Gtk.StateFlags.ACTIVE,
                               style.COLOR_BUTTON_GREY)
    page_widget.append(alignment)
    page_widget.set_visible(True)

    return (page_widget, alignment)


def _get_embedded_page(page_widget):
    if hasattr(page_widget, "get_first_child"):
         first = page_widget.get_first_child()
    elif hasattr(page_widget, "get_child"):
         first = page_widget.get_child()
    else:
         first = None
 
    if first is not None and hasattr(first, "get_first_child"):
         return first.get_first_child()
    return first

def _paint_arrow(widget, cr, angle):
    alloc = widget.get_allocation()

    arrow_size = style.TOOLBAR_ARROW_SIZE / 2
    y = alloc.height - arrow_size
    x = (alloc.width - arrow_size) / 2

    context = widget.get_style_context()
    context.add_class('toolitem')

    Gtk.render_arrow(context, cr, angle, x, y, arrow_size)


def _parse_rgba(color):
    # If it's already a Gdk.RGBA, just return its components
    if hasattr(color, 'red') and hasattr(color, 'green') and hasattr(color, 'blue') and hasattr(color, 'alpha'):
        return (color.red, color.green, color.blue, color.alpha)

    # If it's a tuple/list, assume up to 4 channels
    if isinstance(color, (tuple, list)):
        r, g, b = color[:3]
        a = color[3] if len(color) > 3 else 1.0
        return (r, g, b, a)

    # Fallback to white
    return (1.0, 1.0, 1.0, 1.0)

def _override_background_color(widget, state, color):
    r, g, b, a = _parse_rgba(color)
    css_color = f"rgba({int(r * 255)}, {int(g * 255)}, {int(b * 255)}, {a})"
    style_context = widget.get_style_context()
    style_context.add_class('custom-bg')
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(f"""
        .custom-bg {{
            background-color: {css_color};
        }}
    """.encode('utf-8'))
    style_context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


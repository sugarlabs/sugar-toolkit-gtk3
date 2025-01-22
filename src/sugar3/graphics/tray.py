# Copyright (C) 2007, One Laptop Per Child
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
from gi.repository import Gtk
from gi.repository import Gdk

from sugar3.graphics import style
from sugar3.graphics.palette import ToolInvoker
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.icon import Icon


_PREVIOUS_PAGE = 0
_NEXT_PAGE = 1


if not hasattr(GObject.ParamFlags, 'READWRITE'):
    GObject.ParamFlags.READWRITE = GObject.ParamFlags.WRITABLE | \
        GObject.ParamFlags.READABLE


class _TrayViewport(Gtk.Viewport):

    __gproperties__ = {
        'scrollable': (bool, None, None, False, GObject.ParamFlags.READABLE),
        'can-scroll-prev': (bool, None, None, False,
                            GObject.ParamFlags.READABLE),
        'can-scroll-next': (bool, None, None, False,
                            GObject.ParamFlags.READABLE),
    }

    def __init__(self, orientation):
        self.orientation = orientation
        self._scrollable = False
        self._can_scroll_next = False
        self._can_scroll_prev = False

        Gtk.Viewport.__init__(self)

        self.set_shadow_type(Gtk.ShadowType.NONE)

        self.traybar = Gtk.Toolbar()
        self.traybar.set_orientation(orientation)
        self.traybar.set_show_arrow(False)
        self.add(self.traybar)
        self.traybar.set_visible(True)

        self.connect('size-allocate', self._size_allocate_cb)

        if self.orientation == Gtk.Orientation.HORIZONTAL:
            adj = self.get_hadjustment()
        else:
            adj = self.get_vadjustment()
        adj.connect('changed', self._adjustment_changed_cb)
        adj.connect('value-changed', self._adjustment_changed_cb)

    def scroll(self, direction):
        if direction == _PREVIOUS_PAGE:
            self._scroll_previous()
        elif direction == _NEXT_PAGE:
            self._scroll_next()

    def scroll_to_item(self, item):
        """This function scrolls the viewport so that item will be visible."""
        assert item in self.traybar.get_children()

        # Get the allocation, and make sure that it is visible
        allocation = item.get_allocation()
        if self.orientation == Gtk.Orientation.HORIZONTAL:
            adj = self.get_hadjustment()
            start = allocation.x
            stop = allocation.x + allocation.width
        else:
            adj = self.get_vadjustment()
            start = allocation.y
            stop = allocation.y + allocation.height

        if start < adj.get_value():
            adj.set_value(start)
        elif stop > adj.get_value() + adj.get_page_size():
            adj.set_value(stop - adj.get_page_size())

    def _scroll_next(self):
        allocation = self.get_allocation()
        if self.orientation == Gtk.Orientation.HORIZONTAL:
            adj = self.get_hadjustment()
            new_value = adj.get_value() + allocation.width
            adj.set_value(min(new_value, adj.get_upper() - allocation.width))
        else:
            adj = self.get_vadjustment()
            new_value = adj.get_value() + allocation.height
            adj.set_value(min(new_value, adj.get_upper() - allocation.height))

    def _scroll_previous(self):
        allocation = self.get_allocation()
        if self.orientation == Gtk.Orientation.HORIZONTAL:
            adj = self.get_hadjustment()
            new_value = adj.get_value() - allocation.width
            adj.set_value(max(adj.get_lower(), new_value))
        else:
            adj = self.get_vadjustment()
            new_value = adj.get_value() - allocation.height
            adj.set_value(max(adj.get_lower(), new_value))

    def do_get_preferred_width(self):
        if self.orientation == Gtk.Orientation.HORIZONTAL:
            min_width, nat_width = Gtk.Viewport.do_get_preferred_width(self)
            return 0, nat_width
        child_minimum, child_natural = self.get_child().get_preferred_size()
        return child_minimum.width, child_natural.width

    def do_get_preferred_height(self):
        if self.orientation != Gtk.Orientation.HORIZONTAL:
            min_height, nat_height = Gtk.Viewport.do_get_preferred_height(self)
            return 0, nat_height
        child_minimum, child_natural = self.get_child().get_preferred_size()
        return child_minimum.height, child_natural.height

    def do_get_property(self, pspec):
        if pspec.name == 'scrollable':
            return self._scrollable
        elif pspec.name == 'can-scroll-next':
            return self._can_scroll_next
        elif pspec.name == 'can-scroll-prev':
            return self._can_scroll_prev

    def _size_allocate_cb(self, viewport, allocation):
        if allocation.width == 1 and allocation.height == 1:
            # HACK: the first time this callback is called 'width' and
            # 'height' are 1 so we mark the Viewport as scrollable and
            # we show the Prev / Next buttons
            return

        bar_minimum, bar_natural = self.traybar.get_preferred_size()

        if self.orientation == Gtk.Orientation.HORIZONTAL:
            scrollable = bar_minimum.width > allocation.width
        else:
            scrollable = bar_minimum.height > allocation.height

        if scrollable != self._scrollable:
            self._scrollable = scrollable
            self.notify('scrollable')

    def _adjustment_changed_cb(self, adjustment):
        if adjustment.get_value() <= adjustment.get_lower():
            can_scroll_prev = False
        else:
            can_scroll_prev = True

        if adjustment.get_value() + adjustment.get_page_size() >= \
           adjustment.get_upper():
            can_scroll_next = False
        else:
            can_scroll_next = True

        if can_scroll_prev != self._can_scroll_prev:
            self._can_scroll_prev = can_scroll_prev
            self.notify('can-scroll-prev')

        if can_scroll_next != self._can_scroll_next:
            self._can_scroll_next = can_scroll_next
            self.notify('can-scroll-next')


class _TrayScrollButton(ToolButton):

    __gtype_name__ = 'SugarTrayScrollButton'

    def __init__(self, icon_name, scroll_direction):
        ToolButton.__init__(self)
        self._viewport = None

        self._scroll_direction = scroll_direction

        self.set_size_request(style.GRID_CELL_SIZE, style.GRID_CELL_SIZE)

        self.icon = Icon(icon_name=icon_name,
                         pixel_size=style.SMALL_ICON_SIZE)
        self.set_child(self.icon)
        self.icon.set_visible(True)

        self.connect('clicked', self._clicked_cb)

    def set_viewport(self, viewport):
        self._viewport = viewport
        self._viewport.connect('notify::scrollable',
                               self._viewport_scrollable_changed_cb)

        if self._scroll_direction == _PREVIOUS_PAGE:
            self._viewport.connect('notify::can-scroll-prev',
                                   self._viewport_can_scroll_dir_changed_cb)
            self.set_sensitive(self._viewport.props.can_scroll_prev)
        else:
            self._viewport.connect('notify::can-scroll-next',
                                   self._viewport_can_scroll_dir_changed_cb)
            self.set_sensitive(self._viewport.props.can_scroll_next)

    def _viewport_scrollable_changed_cb(self, viewport, pspec):
        self.props.visible = self._viewport.props.scrollable

    def _viewport_can_scroll_dir_changed_cb(self, viewport, pspec):
        if self._scroll_direction == _PREVIOUS_PAGE:
            sensitive = self._viewport.props.can_scroll_prev
        else:
            sensitive = self._viewport.props.can_scroll_next

        self.set_sensitive(sensitive)

    def _clicked_cb(self, button):
        self._viewport.scroll(self._scroll_direction)

    viewport = property(fset=set_viewport)


ALIGN_TO_START = 0
ALIGN_TO_END = 1


class HTray(Gtk.Box):

    __gtype_name__ = 'SugarHTray'

    __gproperties__ = {
        'align': (int, None, None, 0, 1, ALIGN_TO_START,
                  GObject.ParamFlags.READWRITE |
                  GObject.ParamFlags.CONSTRUCT_ONLY),
        'drag-active': (bool, None, None, False, GObject.ParamFlags.READWRITE),
    }

    def __init__(self, **kwargs):
        self._drag_active = False
        self.align = ALIGN_TO_START

        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL, **kwargs)

        scroll_left = _TrayScrollButton('go-left', _PREVIOUS_PAGE)
        self.append(scroll_left)

        self._viewport = _TrayViewport(Gtk.Orientation.HORIZONTAL)
        self.append(self._viewport)
        self._viewport.set_visible(True)

        scroll_right = _TrayScrollButton('go-right', _NEXT_PAGE)
        self.append(scroll_right)

        scroll_left.viewport = self._viewport
        scroll_right.viewport = self._viewport

        if self.align == ALIGN_TO_END:
            spacer = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
            spacer.set_size_request(0, 0)
            self._viewport.traybar.insert(spacer, 0)
            spacer.set_visible(True)

    def do_set_property(self, pspec, value):
        if pspec.name == 'align':
            self.align = value
        elif pspec.name == 'drag-active':
            self._set_drag_active(value)
        else:
            raise AssertionError

    def do_get_property(self, pspec):
        if pspec.name == 'align':
            return self.align
        elif pspec.name == 'drag-active':
            return self._drag_active
        else:
            raise AssertionError

    def _set_drag_active(self, active):
        if self._drag_active != active:
            self._drag_active = active
            if self._drag_active:
                self._viewport.traybar.override_background_color(
                    Gtk.StateFlags.NORMAL,
                    style.COLOR_BLACK)
            else:
                self._viewport.traybar.override_background_color(Gtk.StateFlags.NORMAL, None)

    def get_children(self):
        children = self._viewport.traybar.get_children()[:]
        if self.align == ALIGN_TO_END:
            children = children[1:]
        return children

    def add_item(self, item, index=-1):
        if self.align == ALIGN_TO_END and index > -1:
            index += 1
        self._viewport.traybar.insert(item, index)

    def remove_item(self, item):
        self._viewport.traybar.remove(item)

    def get_item_index(self, item):
        index = self._viewport.traybar.get_item_index(item)
        if self.align == ALIGN_TO_END:
            index -= 1
        return index

    def scroll_to_item(self, item):
        self._viewport.scroll_to_item(item)


if hasattr(HTray, 'set_css_name'):
    HTray.set_css_name('htray')


class VTray(Gtk.Box):

    __gtype_name__ = 'SugarVTray'

    __gproperties__ = {
        'align': (int, None, None, 0, 1, ALIGN_TO_START,
                  GObject.ParamFlags.READWRITE |
                  GObject.ParamFlags.CONSTRUCT_ONLY),
        'drag-active': (bool, None, None, False, GObject.ParamFlags.READWRITE),
    }

    def __init__(self, **kwargs):
        self._drag_active = False
        self.align = ALIGN_TO_START

        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, **kwargs)

        scroll_up = _TrayScrollButton('go-up', _PREVIOUS_PAGE)
        self.append(scroll_up)

        self._viewport = _TrayViewport(Gtk.Orientation.VERTICAL)
        self.append(self._viewport)
        self._viewport.set_visible(True)

        scroll_down = _TrayScrollButton('go-down', _NEXT_PAGE)
        self.append(scroll_down)

        scroll_up.viewport = self._viewport
        scroll_down.viewport = self._viewport

        if self.align == ALIGN_TO_END:
            spacer = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            spacer.set_size_request(0, 0)
            self._viewport.traybar.insert(spacer, 0)
            spacer.set_visible(True)

    def do_set_property(self, pspec, value):
        if pspec.name == 'align':
            self.align = value
        elif pspec.name == 'drag-active':
            self._set_drag_active(value)
        else:
            raise AssertionError

    def do_get_property(self, pspec):
        if pspec.name == 'align':
            return self.align
        elif pspec.name == 'drag-active':
            return self._drag_active
        else:
            raise AssertionError

    def _set_drag_active(self, active):
        if self._drag_active != active:
            self._drag_active = active
            if self._drag_active:
                self._viewport.traybar.override_background_color(
                    Gtk.StateFlags.NORMAL,
                    style.COLOR_BLACK)
            else:
                self._viewport.traybar.override_background_color(Gtk.StateFlags.NORMAL, None)

    def get_children(self):
        children = self._viewport.traybar.get_children()[:]
        if self.align == ALIGN_TO_END:
            children = children[1:]
        return children

    def add_item(self, item, index=-1):
        if self.align == ALIGN_TO_END and index > -1:
            index += 1
        self._viewport.traybar.insert(item, index)

    def remove_item(self, item):
        self._viewport.traybar.remove(item)

    def get_item_index(self, item):
        index = self._viewport.traybar.get_item_index(item)
        if self.align == ALIGN_TO_END:
            index -= 1
        return index

    def scroll_to_item(self, item):
        self._viewport.scroll_to_item(item)


if hasattr(VTray, 'set_css_name'):
    VTray.set_css_name('VTray')


class TrayButton(ToolButton):

    def __init__(self, **kwargs):
        ToolButton.__init__(self, **kwargs)


class _IconWidget(Gtk.Box):

    __gtype_name__ = 'SugarTrayIconWidget'

    def __init__(self, icon_name=None, xo_color=None):
        Gtk.Box.__init__(self)

        self.set_app_paintable(True)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.TOUCH_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)

        self._icon = Icon(icon_name=icon_name, xo_color=xo_color,
                          pixel_size=style.STANDARD_ICON_SIZE)
        self.append(self._icon)
        self._icon.set_visible(True)

    def do_draw(self, cr):
        palette = self.get_parent().palette

        if palette and palette.is_up():
            allocation = self.get_allocation()
            # draw a black background, has been done by the engine before
            cr.set_source_rgb(0, 0, 0)
            cr.rectangle(0, 0, allocation.width, allocation.height)
            cr.paint()

        Gtk.Box.do_draw(self, cr)

        if palette and palette.is_up():
            invoker = palette.props.invoker
            invoker.draw_rectangle(cr, palette)

        return False

    def get_icon(self):
        return self._icon


class TrayIcon(Gtk.ToolItem):

    __gtype_name__ = 'SugarTrayIcon'

    def __init__(self, icon_name=None, xo_color=None):
        Gtk.ToolItem.__init__(self)

        self._icon_widget = _IconWidget(icon_name, xo_color)
        self.add(self._icon_widget)
        self._icon_widget.set_visible(True)

        self._palette_invoker = ToolInvoker(self)

        self.set_size_request(style.GRID_CELL_SIZE, style.GRID_CELL_SIZE)

        self.connect('destroy', self.__destroy_cb)

    def __destroy_cb(self, icon):
        if self._palette_invoker is not None:
            self._palette_invoker.detach()

    def create_palette(self):
        return None

    def get_palette(self):
        return self._palette_invoker.palette

    def set_palette(self, palette):
        self._palette_invoker.palette = palette

    palette = GObject.Property(
        type=object, setter=set_palette, getter=get_palette)

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = GObject.Property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker)

    def get_icon(self):
        return self._icon_widget.get_icon()
    icon = property(get_icon, None)

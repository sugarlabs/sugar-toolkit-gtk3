# Copyright (C) 2006-2007 Red Hat, Inc.
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
A small fixed size picture, typically used to decorate components.

STABLE.
"""

import re
import math
import logging

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Rsvg
import cairo

from sugar3.graphics import style
from sugar3.graphics.xocolor import XoColor
from sugar3.util import LRU

_BADGE_SIZE = 0.45


class _SVGLoader(object):

    def __init__(self):
        self._cache = LRU(50)

    def load(self, file_name, entities, cache):
        if file_name in self._cache:
            icon = self._cache[file_name]
        else:
            icon_file = open(file_name, 'r')
            icon = icon_file.read()
            icon_file.close()

            if cache:
                self._cache[file_name] = icon

        for entity, value in entities.items():
            if isinstance(value, basestring):
                xml = '<!ENTITY %s "%s">' % (entity, value)
                icon = re.sub('<!ENTITY %s .*>' % entity, xml, icon)
            else:
                logging.error(
                    'Icon %s, entity %s is invalid.', file_name, entity)

        return Rsvg.Handle.new_from_data(icon)


class _IconInfo(object):

    def __init__(self):
        self.file_name = None
        self.attach_x = 0
        self.attach_y = 0


class _BadgeInfo(object):

    def __init__(self):
        self.attach_x = 0
        self.attach_y = 0
        self.size = 0
        self.icon_padding = 0


class _IconBuffer(object):

    _surface_cache = LRU(50)
    _loader = _SVGLoader()

    def __init__(self):
        self.icon_name = None
        self.icon_size = None
        self.file_name = None
        self.fill_color = None
        self.background_color = None
        self.stroke_color = None
        self.badge_name = None
        self.width = None
        self.height = None
        self.cache = False
        self.scale = 1.0

    def _get_cache_key(self, sensitive):
        if self.background_color is None:
            color = None
        else:
            color = (self.background_color.red, self.background_color.green,
                     self.background_color.blue)
        return (self.icon_name, self.file_name, self.fill_color,
                self.stroke_color, self.badge_name, self.width, self.height,
                color, sensitive)

    def _load_svg(self, file_name):
        entities = {}
        if self.fill_color:
            entities['fill_color'] = self.fill_color
        if self.stroke_color:
            entities['stroke_color'] = self.stroke_color

        return self._loader.load(file_name, entities, self.cache)

    def _get_attach_points(self, info, size_request):
        has_attach_points_, attach_points = info.get_attach_points()

        if attach_points:
            attach_x = float(attach_points[0].x) / size_request
            attach_y = float(attach_points[0].y) / size_request
        else:
            attach_x = attach_y = 0

        return attach_x, attach_y

    def _get_icon_info(self):
        icon_info = _IconInfo()

        if self.file_name:
            icon_info.file_name = self.file_name
        elif self.icon_name:
            theme = Gtk.IconTheme.get_default()

            size = 50
            if self.width != None:
                size = self.width

            info = theme.lookup_icon(self.icon_name, int(size), 0)
            if info:
                attach_x, attach_y = self._get_attach_points(info, size)

                icon_info.file_name = info.get_filename()
                icon_info.attach_x = attach_x
                icon_info.attach_y = attach_y

                del info
            else:
                logging.warning('No icon with the name %s was found in the '
                    'theme.', self.icon_name)

        return icon_info

    def _draw_badge(self, context, size, sensitive, widget):
        theme = Gtk.IconTheme.get_default()
        badge_info = theme.lookup_icon(self.badge_name, int(size), 0)
        if badge_info:
            badge_file_name = badge_info.get_filename()
            if badge_file_name.endswith('.svg'):
                handle = self._loader.load(badge_file_name, {}, self.cache)

                icon_width = handle.props.width
                icon_height = handle.props.height

                pixbuf = handle.get_pixbuf()
            else:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(badge_file_name)

                icon_width = pixbuf.get_width()
                icon_height = pixbuf.get_height()

            context.scale(float(size) / icon_width,
                          float(size) / icon_height)

            if not sensitive:
                pixbuf = self._get_insensitive_pixbuf(pixbuf, widget)
            Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
            context.paint()

    def _get_size(self, icon_width, icon_height, padding):
        if self.width is not None and self.height is not None:
            width = self.width + padding
            height = self.height + padding
        else:
            width = icon_width + padding
            height = icon_height + padding

        return width, height

    def _get_badge_info(self, icon_info, icon_width, icon_height):
        info = _BadgeInfo()
        if self.badge_name is None:
            return info

        info.size = int(_BADGE_SIZE * icon_width)
        info.attach_x = int(icon_info.attach_x * icon_width - info.size / 2)
        info.attach_y = int(icon_info.attach_y * icon_height - info.size / 2)

        if info.attach_x < 0 or info.attach_y < 0:
            info.icon_padding = max(-info.attach_x, -info.attach_y)
        elif info.attach_x + info.size > icon_width or \
             info.attach_y + info.size > icon_height:
            x_padding = info.attach_x + info.size - icon_width
            y_padding = info.attach_y + info.size - icon_height
            info.icon_padding = max(x_padding, y_padding)

        return info

    def _get_xo_color(self):
        if self.stroke_color and self.fill_color:
            return XoColor('%s,%s' % (self.stroke_color, self.fill_color))
        else:
            return None

    def _set_xo_color(self, xo_color):
        if xo_color:
            self.stroke_color = xo_color.get_stroke_color()
            self.fill_color = xo_color.get_fill_color()
        else:
            self.stroke_color = None
            self.fill_color = None

    def _get_insensitive_pixbuf(self, pixbuf, widget):
        if not (widget and widget.get_style()):
            return pixbuf

        icon_source = Gtk.IconSource()
        # Special size meaning "don't touch"
        icon_source.set_size(-1)
        icon_source.set_pixbuf(pixbuf)
        icon_source.set_state(Gtk.StateType.INSENSITIVE)
        icon_source.set_direction_wildcarded(False)
        icon_source.set_size_wildcarded(False)

        style = widget.get_style()
        pixbuf = style.render_icon(icon_source, widget.get_direction(),
                                   Gtk.StateType.INSENSITIVE, -1, widget,
                                   'sugar-icon')

        return pixbuf

    def get_surface(self, sensitive=True, widget=None):
        cache_key = self._get_cache_key(sensitive)
        if cache_key in self._surface_cache:
            return self._surface_cache[cache_key]

        icon_info = self._get_icon_info()
        if icon_info.file_name is None:
            return None

        is_svg = icon_info.file_name.endswith('.svg')

        if is_svg:
            handle = self._load_svg(icon_info.file_name)
            icon_width = handle.props.width
            icon_height = handle.props.height
        else:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_info.file_name)
            icon_width = pixbuf.get_width()
            icon_height = pixbuf.get_height()

        badge_info = self._get_badge_info(icon_info, icon_width, icon_height)

        padding = badge_info.icon_padding
        width, height = self._get_size(icon_width, icon_height, padding)
        if self.background_color is None:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width),
                                         int(height))
            context = cairo.Context(surface)
        else:
            surface = cairo.ImageSurface(cairo.FORMAT_RGB24, int(width),
                                         int(height))
            context = cairo.Context(surface)
            context.set_source_color(self.background_color)
            context.paint()

        context.scale(float(width) / (icon_width + padding * 2),
                      float(height) / (icon_height + padding * 2))
        context.save()

        context.translate(padding, padding)
        if is_svg:
            if sensitive:
                handle.render_cairo(context)
            else:
                pixbuf = handle.get_pixbuf()
                pixbuf = self._get_insensitive_pixbuf(pixbuf, widget)

                Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
                context.paint()
        else:
            if not sensitive:
                pixbuf = self._get_insensitive_pixbuf(pixbuf, widget)
            Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
            context.paint()

        if self.badge_name:
            context.restore()
            context.translate(badge_info.attach_x, badge_info.attach_y)
            self._draw_badge(context, badge_info.size, sensitive, widget)

        self._surface_cache[cache_key] = surface

        return surface

    xo_color = property(_get_xo_color, _set_xo_color)


class Icon(Gtk.Image):

    __gtype_name__ = 'SugarIcon'

    def __init__(self, **kwargs):
        self._buffer = _IconBuffer()
        # HACK: need to keep a reference to the path so it doesn't get garbage
        # collected while it's still used if it's a sugar3.util.TempFilePath.
        # See #1175
        self._file = None
        self._alpha = 1.0
        self._scale = 1.0

        GObject.GObject.__init__(self, **kwargs)

    def get_file(self):
        return self._file

    def set_file(self, file_name):
        self._file = file_name
        self._buffer.file_name = file_name

    file = GObject.property(type=object, setter=set_file, getter=get_file)

    def _sync_image_properties(self):
        if self._buffer.icon_name != self.props.icon_name:
            self._buffer.icon_name = self.props.icon_name

        if self._buffer.file_name != self.props.file:
            self._buffer.file_name = self.props.file

        if self.props.pixel_size == -1:
            valid_, width, height = Gtk.icon_size_lookup(self.props.icon_size)
        else:
            width = height = self.props.pixel_size
        if self._buffer.width != width or self._buffer.height != height:
            self._buffer.width = width
            self._buffer.height = height

    def _icon_size_changed_cb(self, image, pspec):
        self._buffer.icon_size = self.props.icon_size

    def _icon_name_changed_cb(self, image, pspec):
        self._buffer.icon_name = self.props.icon_name

    def _file_changed_cb(self, image, pspec):
        self._buffer.file_name = self.props.file

    def do_get_preferred_height(self):
        self._sync_image_properties()
        surface = self._buffer.get_surface()
        if surface:
            height = surface.get_height()
        elif self._buffer.height:
            height = self._buffer.height
        else:
            height = 0
        return (height, height)

    def do_get_preferred_width(self):
        self._sync_image_properties()
        surface = self._buffer.get_surface()
        if surface:
            width = surface.get_width()
        elif self._buffer.width:
            width = self._buffer.width
        else:
            width = 0
        return (width, width)

    def do_draw(self, cr):
        self._sync_image_properties()
        sensitive = (self.is_sensitive())
        surface = self._buffer.get_surface(sensitive, self)
        if surface is None:
            return

        xpad, ypad = self.get_padding()
        xalign, yalign = self.get_alignment()
        requisition = self.get_child_requisition()
        if self.get_direction() != Gtk.TextDirection.LTR:
            xalign = 1.0 - xalign

        allocation = self.get_allocation()
        x = math.floor(xpad +
            (allocation.width - requisition.width) * xalign)
        y = math.floor(ypad +
            (allocation.height - requisition.height) * yalign)

        if self._scale != 1.0:
            cr.scale(self._scale, self._scale)

            margin = self._buffer.width * (1 - self._scale) / 2
            x, y = x + margin, y + margin

            x = x / self._scale
            y = y / self._scale

        cr.set_source_surface(surface, x, y)

        if self._alpha == 1.0:
            cr.paint()
        else:
            cr.paint_with_alpha(self._alpha)

    def set_xo_color(self, value):
        if self._buffer.xo_color != value:
            self._buffer.xo_color = value
            self.queue_draw()

    xo_color = GObject.property(
        type=object, getter=None, setter=set_xo_color)

    def set_fill_color(self, value):
        if self._buffer.fill_color != value:
            self._buffer.fill_color = value
            self.queue_draw()

    def get_fill_color(self):
        return self._buffer.fill_color

    fill_color = GObject.property(
        type=object, getter=get_fill_color, setter=set_fill_color)

    def set_stroke_color(self, value):
        if self._buffer.stroke_color != value:
            self._buffer.stroke_color = value
            self.queue_draw()

    def get_stroke_color(self):
        return self._buffer.stroke_color

    stroke_color = GObject.property(
        type=object, getter=get_stroke_color, setter=set_stroke_color)

    def set_badge_name(self, value):
        if self._buffer.badge_name != value:
            self._buffer.badge_name = value
            self.queue_resize()

    def get_badge_name(self):
        return self._buffer.badge_name

    badge_name = GObject.property(
        type=str, getter=get_badge_name, setter=set_badge_name)

    def set_alpha(self, value):
        if self._alpha != value:
            self._alpha = value
            self.queue_draw()

    alpha = GObject.property(
        type=float, setter=set_alpha)

    def set_scale(self, value):
        if self._scale != value:
            self._scale = value
            self.queue_draw()

    scale = GObject.property(
        type=float, setter=set_scale)


class EventIcon(Gtk.EventBox):
    """
    An Icon class that provides access to mouse events and that can act as a
    cursor-positioned palette invoker.
    """

    __gtype_name__ = 'SugarEventIcon'

    def __init__(self, **kwargs):
        self._buffer = _IconBuffer()
        self._alpha = 1.0

        Gtk.EventBox.__init__(self)
        self.set_visible_window(False)
        self.set_above_child(True)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.TOUCH_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)
        for key, value in kwargs.iteritems():
            self.set_property(key, value)

        from sugar3.graphics.palette import CursorInvoker
        self._palette_invoker = CursorInvoker()
        self._palette_invoker.attach(self)
        self.connect('destroy', self.__destroy_cb)

    def do_draw(self, cr):
        surface = self._buffer.get_surface()
        if surface:
            allocation = self.get_allocation()

            x = (allocation.width - surface.get_width()) / 2
            y = (allocation.height - surface.get_height()) / 2

            cr.set_source_surface(surface, x, y)
            if self._alpha == 1.0:
                cr.paint()
            else:
                cr.paint_with_alpha(self._alpha)

    def do_get_preferred_height(self):
        surface = self._buffer.get_surface()
        if surface:
            height = surface.get_height()
        elif self._buffer.height:
            height = self._buffer.height
        else:
            height = 0
        return (height, height)

    def do_get_preferred_width(self):
        surface = self._buffer.get_surface()
        if surface:
            width = surface.get_width()
        elif self._buffer.width:
            width = self._buffer.width
        else:
            width = 0
        return (width, width)

    def __destroy_cb(self, icon):
        if self._palette_invoker is not None:
            self._palette_invoker.detach()

    def set_file_name(self, value):
        if self._buffer.file_name != value:
            self._buffer.file_name = value
            self.queue_draw()

    def get_file_name(self):
        return self._buffer.file_name

    file_name = GObject.property(
        type=object, getter=get_file_name, setter=set_file_name)

    def set_icon_name(self, value):
        if self._buffer.icon_name != value:
            self._buffer.icon_name = value
            self.queue_draw()

    def get_icon_name(self):
        return self._buffer.icon_name

    icon_name = GObject.property(
        type=object, getter=get_icon_name, setter=set_icon_name)

    def set_xo_color(self, value):
        if self._buffer.xo_color != value:
            self._buffer.xo_color = value
            self.queue_draw()

    xo_color = GObject.property(
        type=object, getter=None, setter=set_xo_color)

    def set_fill_color(self, value):
        if self._buffer.fill_color != value:
            self._buffer.fill_color = value
            self.queue_draw()

    def get_fill_color(self):
        return self._buffer.fill_color

    fill_color = GObject.property(
        type=object, getter=get_fill_color, setter=set_fill_color)

    def set_stroke_color(self, value):
        if self._buffer.stroke_color != value:
            self._buffer.stroke_color = value
            self.queue_draw()

    def get_stroke_color(self):
        return self._buffer.stroke_color

    stroke_color = GObject.property(
        type=object, getter=get_stroke_color, setter=set_stroke_color)

    def set_background_color(self, value):
        if self._buffer.background_color != value:
            self._buffer.background_color = value
            self.queue_draw()

    def get_background_color(self):
        return self._buffer.background_color

    background_color = GObject.property(
        type=object, getter=get_background_color, setter=set_background_color)

    def set_size(self, value):
        if self._buffer.width != value:
            self._buffer.width = value
            self._buffer.height = value
            self.queue_resize()

    def get_size(self):
        return self._buffer.width

    pixel_size = GObject.property(
        type=object, getter=get_size, setter=set_size)

    def set_scale(self, value):
        if self._buffer.scale != value:
            self._buffer.scale = value
            self.queue_resize()

    def get_scale(self):
        return self._buffer.scale

    scale = GObject.property(
        type=float, getter=get_scale, setter=set_scale)

    def set_alpha(self, alpha):
        if self._alpha != alpha:
            self._alpha = alpha
            self.queue_draw()

    alpha = GObject.property(
        type=float, setter=set_alpha)

    def set_cache(self, value):
        self._buffer.cache = value

    def get_cache(self):
        return self._buffer.cache

    cache = GObject.property(
        type=bool, default=False, getter=get_cache, setter=set_cache)

    def set_badge_name(self, value):
        if self._buffer.badge_name != value:
            self._buffer.badge_name = value
            self.queue_draw()

    def get_badge_name(self):
        return self._buffer.badge_name

    badge_name = GObject.property(
        type=object, getter=get_badge_name, setter=set_badge_name)

    def create_palette(self):
        return None

    def get_palette(self):
        return self._palette_invoker.palette

    def set_palette(self, palette):
        self._palette_invoker.palette = palette

    palette = GObject.property(
        type=object, setter=set_palette, getter=get_palette)

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = GObject.property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker)

    def set_tooltip(self, text):
        from sugar3.graphics.palette import Palette

        self.set_palette(Palette(text))


class CanvasIcon(EventIcon):
    """
    An EventIcon with active and prelight states, and a styleable
    background.

    If the icon pops up a palette, the prelight state is set until the
    palette pops down.

    """

    __gtype_name__ = 'SugarCanvasIcon'

    def __init__(self, **kwargs):
        EventIcon.__init__(self, **kwargs)

        self.connect('enter-notify-event', self.__enter_notify_event_cb)
        self.connect('leave-notify-event', self.__leave_notify_event_cb)
        self.connect('button-press-event', self.__button_press_event_cb)
        self.connect('button-release-event', self.__button_release_event_cb)

    def connect_to_palette_pop_events(self, palette):
        palette.connect('popup', self.__palette_popup_cb)
        palette.connect('popdown', self.__palette_popdown_cb)

    def do_draw(self, cr):
        """Render a background that fits the allocated space."""
        allocation = self.get_allocation()
        context = self.get_style_context()
        Gtk.render_background(context, cr, 0, 0,
                              allocation.width,
                              allocation.height)

        EventIcon.do_draw(self, cr)

    def __enter_notify_event_cb(self, icon, event):
        self.set_state_flags(self.get_state_flags() | Gtk.StateFlags.PRELIGHT,
                             clear=True)

    def __leave_notify_event_cb(self, icon, event):
        if self.palette and self.palette.is_up():
            return

        self.unset_state_flags(Gtk.StateFlags.PRELIGHT)

    def __button_press_event_cb(self, icon, event):
        if self.palette and not self.palette.is_up():
            self.set_state_flags(self.get_state_flags() | Gtk.StateFlags.ACTIVE,
                                 clear=True)

    def __button_release_event_cb(self, icon, event):
        self.unset_state_flags(Gtk.StateFlags.ACTIVE)

    def __palette_popup_cb(self, palette):
        self.set_state_flags(Gtk.StateFlags.PRELIGHT, clear=True)

    def __palette_popdown_cb(self, palette):
        self.unset_state_flags(Gtk.StateFlags.PRELIGHT)


class CellRendererIcon(Gtk.CellRenderer):

    __gtype_name__ = 'SugarCellRendererIcon'

    __gsignals__ = {
        'clicked': (GObject.SignalFlags.RUN_FIRST, None, [object]),
    }

    def __init__(self, tree_view):
        from sugar3.graphics.palette import CellRendererInvoker

        self._buffer = _IconBuffer()
        self._buffer.cache = True
        self._xo_color = None
        self._fill_color = None
        self._stroke_color = None
        self._prelit_fill_color = None
        self._prelit_stroke_color = None
        self._active_state = False
        self._palette_invoker = CellRendererInvoker()

        Gtk.CellRenderer.__init__(self)

        tree_view.connect('button-press-event',
                          self.__button_press_event_cb)
        tree_view.connect('button-release-event',
                          self.__button_release_event_cb)

        self._palette_invoker.attach_cell_renderer(tree_view, self)

    def __del__(self):
        self._palette_invoker.detach()

    def __button_press_event_cb(self, widget, event):
        if self._point_in_cell_renderer(widget, event.x, event.y):
            self._active_state = True

    def __button_release_event_cb(self, widget, event):
        self._active_state = False

    def create_palette(self):
        return None

    def get_palette_invoker(self):
        return self._palette_invoker

    palette_invoker = GObject.property(type=object, getter=get_palette_invoker)

    def set_file_name(self, value):
        if self._buffer.file_name != value:
            self._buffer.file_name = value

    file_name = GObject.property(type=str, setter=set_file_name)

    def set_icon_name(self, value):
        if self._buffer.icon_name != value:
            self._buffer.icon_name = value

    icon_name = GObject.property(type=str, setter=set_icon_name)

    def get_xo_color(self):
        return self._xo_color

    def set_xo_color(self, value):
        self._xo_color = value

    xo_color = GObject.property(type=object,
            getter=get_xo_color, setter=set_xo_color)

    def set_fill_color(self, value):
        if self._fill_color != value:
            self._fill_color = value

    fill_color = GObject.property(type=object, setter=set_fill_color)

    def set_stroke_color(self, value):
        if self._stroke_color != value:
            self._stroke_color = value

    stroke_color = GObject.property(type=object, setter=set_stroke_color)

    def set_prelit_fill_color(self, value):
        if self._prelit_fill_color != value:
            self._prelit_fill_color = value

    prelit_fill_color = GObject.property(type=object,
                                         setter=set_prelit_fill_color)

    def set_prelit_stroke_color(self, value):
        if self._prelit_stroke_color != value:
            self._prelit_stroke_color = value

    prelit_stroke_color = GObject.property(type=object,
                                           setter=set_prelit_stroke_color)

    def set_background_color(self, value):
        if self._buffer.background_color != value:
            self._buffer.background_color = value

    background_color = GObject.property(type=object,
                                        setter=set_background_color)

    def set_size(self, value):
        if self._buffer.width != value:
            self._buffer.width = value
            self._buffer.height = value

    size = GObject.property(type=object, setter=set_size)

    def do_get_size(self, widget, cell_area, x_offset=None, y_offset=None,
                    width=None, height=None):
        width = self._buffer.width + self.props.xpad * 2
        height = self._buffer.height + self.props.ypad * 2
        xoffset = 0
        yoffset = 0

        if width > 0 and height > 0 and cell_area is not None:

            if widget.get_direction() == Gtk.TextDirection.RTL:
                xoffset = 1.0 - self.props.xalign
            else:
                xoffset = self.props.xalign

            xoffset = max(xoffset * (cell_area.width - width), 0)
            yoffset = max(self.props.yalign * (cell_area.height - height), 0)

        return xoffset, yoffset, width, height

    def do_activate(self, event, widget, path, background_area, cell_area,
                    flags):
        pass

    def do_start_editing(self, event, widget, path, background_area, cell_area,
                         flags):
        pass

    def _point_in_cell_renderer(self, tree_view, x=None, y=None):
        """Check if the point with coordinates x, y is inside this icon.

        If the x, y coordinates are not given, they are taken from the
        pointer current position.

        """
        if x is None and y is None:
            x, y = tree_view.get_pointer()
            x, y = tree_view.convert_widget_to_bin_window_coords(x, y)
        pos = tree_view.get_path_at_pos(int(x), int(y))
        if pos is None:
            return False

        path_, column, x, y_ = pos

        for cell_renderer in column.get_cells():
            if cell_renderer == self:
                cell_x, cell_width = column.cell_get_position(cell_renderer)
                if x > cell_x and x < (cell_x + cell_width):
                    return True
                return False

        return False

    def do_render(self, cr, widget, background_area, cell_area, flags):
        context = widget.get_style_context()
        context.save()
        context.add_class("sugar-icon-cell")

        pointer_inside = self._point_in_cell_renderer(widget)

        # The context will have prelight state if the mouse pointer is
        # in the entire row, but we want that state if the pointer is
        # in this cell only:
        if flags & Gtk.CellRendererState.PRELIT:
            if pointer_inside:
                if self._active_state:
                    context.set_state(Gtk.StateFlags.ACTIVE)
            else:
                context.set_state(Gtk.StateFlags.NORMAL)


        Gtk.render_background(context, cr, background_area.x, background_area.y,
                              background_area.width, background_area.height)

        Gtk.render_frame(context, cr, background_area.x, background_area.y,
                         background_area.width, background_area.height)

        if self._xo_color is not None:
            stroke_color = self._xo_color.get_stroke_color()
            fill_color = self._xo_color.get_fill_color()
            prelit_fill_color = None
            prelit_stroke_color = None
        else:
            stroke_color = self._stroke_color
            fill_color = self._fill_color
            prelit_fill_color = self._prelit_fill_color
            prelit_stroke_color = self._prelit_stroke_color

        has_prelit_colors = None not in [prelit_fill_color,
                                         prelit_stroke_color]

        if flags & Gtk.CellRendererState.PRELIT and has_prelit_colors and \
                pointer_inside:

            self._buffer.fill_color = prelit_fill_color
            self._buffer.stroke_color = prelit_stroke_color
        else:
            self._buffer.fill_color = fill_color
            self._buffer.stroke_color = stroke_color

        surface = self._buffer.get_surface()
        if surface is None:
            return

        xoffset, yoffset, width_, height_ = self.do_get_size(widget, cell_area)

        x = cell_area.x + xoffset
        y = cell_area.y + yoffset

        cr.set_source_surface(surface, math.floor(x), math.floor(y))
        cr.rectangle(cell_area.x, cell_area.y, cell_area.width,
                     cell_area.height)
        cr.clip()
        cr.paint()


def get_icon_state(base_name, perc, step=5):
    strength = round(perc / step) * step
    icon_theme = Gtk.IconTheme.get_default()

    while strength <= 100 and strength >= 0:
        icon_name = '%s-%03d' % (base_name, strength)
        if icon_theme.has_icon(icon_name):
            return icon_name

        strength = strength + step


def get_icon_file_name(icon_name):
    icon_theme = Gtk.IconTheme.get_default()
    info = icon_theme.lookup_icon(icon_name, Gtk.IconSize.LARGE_TOOLBAR, 0)
    if not info:
        return None
    filename = info.get_filename()
    del info
    return filename


def get_surface(**kwargs):
    """Get cached cairo surface.

        Keyword arguments:
        icon_name        -- name of icon to load, default None
        file_name        -- path to image file, default None
        fill_color       -- for svg images, change default fill color
                            default None
        stroke_color     -- for svg images, change default stroke color
                            default None
        background_color -- draw background or surface will be transparent
                            default None
        badge_name       -- name of icon which will be drawn on top of
                            original image, default None
        width            -- change image width, default None
        height           -- change image height, default None
        cache            -- if image is svg, keep svg file content for later
        scale            -- scale image, default 1.0

        Return: cairo surface or None if image was not found

        """
    icon = _IconBuffer()
    for key, value in kwargs.items():
        icon.__setattr__(key, value)
    return icon.get_surface()

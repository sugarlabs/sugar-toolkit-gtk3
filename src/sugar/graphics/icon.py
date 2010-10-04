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

import gobject
import gtk
import hippo
import cairo

from sugar.graphics.xocolor import XoColor
from sugar.util import LRU


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

        import rsvg # XXX this is very slow!  why?
        return rsvg.Handle(data=icon)


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
        attach_points = info.get_attach_points()

        if attach_points:
            attach_x = float(attach_points[0][0]) / size_request
            attach_y = float(attach_points[0][1]) / size_request
        else:
            attach_x = attach_y = 0

        return attach_x, attach_y

    def _get_icon_info(self):
        icon_info = _IconInfo()

        if self.file_name:
            icon_info.file_name = self.file_name
        elif self.icon_name:
            theme = gtk.icon_theme_get_default()

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
        theme = gtk.icon_theme_get_default()
        badge_info = theme.lookup_icon(self.badge_name, int(size), 0)
        if badge_info:
            badge_file_name = badge_info.get_filename()
            if badge_file_name.endswith('.svg'):
                handle = self._loader.load(badge_file_name, {}, self.cache)

                dimensions = handle.get_dimension_data()
                icon_width = int(dimensions[0])
                icon_height = int(dimensions[1])

                pixbuf = handle.get_pixbuf()
            else:
                pixbuf = gtk.gdk.pixbuf_new_from_file(badge_file_name)

                icon_width = pixbuf.get_width()
                icon_height = pixbuf.get_height()

            context.scale(float(size) / icon_width,
                          float(size) / icon_height)

            if not sensitive:
                pixbuf = self._get_insensitive_pixbuf(pixbuf, widget)
            surface = hippo.cairo_surface_from_gdk_pixbuf(pixbuf)
            context.set_source_surface(surface, 0, 0)
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
        if not (widget and widget.style):
            return pixbuf

        icon_source = gtk.IconSource()
        # Special size meaning "don't touch"
        icon_source.set_size(-1)
        icon_source.set_pixbuf(pixbuf)
        icon_source.set_state(gtk.STATE_INSENSITIVE)
        icon_source.set_direction_wildcarded(False)
        icon_source.set_size_wildcarded(False)

        # Please note that the pixbuf returned by this function is leaked
        # with current stable versions of pygtk. The relevant bug is
        # http://bugzilla.gnome.org/show_bug.cgi?id=502871
        #   -- 2007-12-14 Benjamin Berg
        pixbuf = widget.style.render_icon(icon_source, widget.get_direction(),
                                          gtk.STATE_INSENSITIVE, -1, widget,
                                          "sugar-icon")

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
            dimensions = handle.get_dimension_data()
            icon_width = int(dimensions[0])
            icon_height = int(dimensions[1])
        else:
            pixbuf = gtk.gdk.pixbuf_new_from_file(icon_info.file_name)
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
            context = gtk.gdk.CairoContext(context)
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

                pixbuf_surface = hippo.cairo_surface_from_gdk_pixbuf(pixbuf)
                context.set_source_surface(pixbuf_surface, 0, 0)
                context.paint()
        else:
            if not sensitive:
                pixbuf = self._get_insensitive_pixbuf(pixbuf, widget)
            pixbuf_surface = hippo.cairo_surface_from_gdk_pixbuf(pixbuf)
            context.set_source_surface(pixbuf_surface, 0, 0)
            context.paint()

        if self.badge_name:
            context.restore()
            context.translate(badge_info.attach_x, badge_info.attach_y)
            self._draw_badge(context, badge_info.size, sensitive, widget)

        self._surface_cache[cache_key] = surface

        return surface

    xo_color = property(_get_xo_color, _set_xo_color)


class Icon(gtk.Image):

    __gtype_name__ = 'SugarIcon'

    def __init__(self, **kwargs):
        self._buffer = _IconBuffer()
        # HACK: need to keep a reference to the path so it doesn't get garbage
        # collected while it's still used if it's a sugar.util.TempFilePath.
        # See #1175
        self._file = None

        gobject.GObject.__init__(self, **kwargs)

    def get_file(self):
        return self._file

    def set_file(self, file_name):
        self._file = file_name
        self._buffer.file_name = file_name

    file = gobject.property(type=object, setter=set_file, getter=get_file)

    def _sync_image_properties(self):
        if self._buffer.icon_name != self.props.icon_name:
            self._buffer.icon_name = self.props.icon_name

        if self._buffer.file_name != self.props.file:
            self._buffer.file_name = self.props.file

        if self.props.pixel_size == -1:
            width, height = gtk.icon_size_lookup(self.props.icon_size)
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

    def do_size_request(self, requisition):
        """
        Parameters
        ----------
        requisition :

        Returns
        -------
        None

        """
        self._sync_image_properties()
        surface = self._buffer.get_surface()
        if surface:
            requisition[0] = surface.get_width()
            requisition[1] = surface.get_height()
        elif self._buffer.width and self._buffer.height:
            requisition[0] = self._buffer.width
            requisition[1] = self._buffer.width
        else:
            requisition[0] = requisition[1] = 0

    def do_expose_event(self, event):
        """
        Parameters
        ----------
        event :

        Returns:
        --------
        None

        """
        self._sync_image_properties()
        sensitive = (self.state != gtk.STATE_INSENSITIVE)
        surface = self._buffer.get_surface(sensitive, self)
        if surface is None:
            return

        xpad, ypad = self.get_padding()
        xalign, yalign = self.get_alignment()
        requisition = self.get_child_requisition()
        if self.get_direction() != gtk.TEXT_DIR_LTR:
            xalign = 1.0 - xalign

        allocation = self.get_allocation()
        x = math.floor(allocation.x + xpad +
            (allocation.width - requisition[0]) * xalign)
        y = math.floor(allocation.y + ypad +
            (allocation.height - requisition[1]) * yalign)

        cr = self.window.cairo_create()
        cr.set_source_surface(surface, x, y)
        cr.paint()

    def set_xo_color(self, value):
        """
        Parameters
        ----------
        value :

        Returns
        -------
        None

        """
        if self._buffer.xo_color != value:
            self._buffer.xo_color = value
            self.queue_draw()

    xo_color = gobject.property(
        type=object, getter=None, setter=set_xo_color)

    def set_fill_color(self, value):
        """
        Parameters
        ----------
        value :

        Returns
        -------
        None

        """
        if self._buffer.fill_color != value:
            self._buffer.fill_color = value
            self.queue_draw()

    def get_fill_color(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        fill_color :

        """
        return self._buffer.fill_color

    fill_color = gobject.property(
        type=object, getter=get_fill_color, setter=set_fill_color)

    def set_stroke_color(self, value):
        """
        Parameters
        ----------
        value :

        Returns
        -------
        None

        """
        if self._buffer.stroke_color != value:
            self._buffer.stroke_color = value
            self.queue_draw()

    def get_stroke_color(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        stroke_color :

        """
        return self._buffer.stroke_color

    stroke_color = gobject.property(
        type=object, getter=get_stroke_color, setter=set_stroke_color)

    def set_badge_name(self, value):
        """
        Parameters
        ----------
        value:

        Returns
        -------
        None

        """
        if self._buffer.badge_name != value:
            self._buffer.badge_name = value
            self.queue_resize()

    def get_badge_name(self):
        return self._buffer.badge_name

    badge_name = gobject.property(
        type=str, getter=get_badge_name, setter=set_badge_name)


class CanvasIcon(hippo.CanvasBox, hippo.CanvasItem):

    __gtype_name__ = 'CanvasIcon'

    def __init__(self, **kwargs):
        from sugar.graphics.palette import CanvasInvoker

        self._buffer = _IconBuffer()
        self._palette_invoker = CanvasInvoker()

        hippo.CanvasBox.__init__(self, **kwargs)

        self._palette_invoker.attach(self)

        self.connect('destroy', self.__destroy_cb)

    def _emit_paint_needed_icon_area(self):
        surface = self._buffer.get_surface()
        if surface:
            width, height = self.get_allocation()
            s_width = surface.get_width()
            s_height = surface.get_height()

            x = (width - s_width) / 2
            y = (height - s_height) / 2

            self.emit_paint_needed(x, y, s_width, s_height)

    def __destroy_cb(self, icon):
        if self._palette_invoker is not None:
            self._palette_invoker.detach()

    def set_file_name(self, value):
        """
        Parameters
        ----------
        value:

        Returns
        -------
        None

        \"\"\"

        """
        if self._buffer.file_name != value:
            self._buffer.file_name = value
            self.emit_paint_needed(0, 0, -1, -1)

    def get_file_name(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        file name :

        """
        return self._buffer.file_name

    file_name = gobject.property(
        type=object, getter=get_file_name, setter=set_file_name)

    def set_icon_name(self, value):
        """
        Parameters
        ----------
        value:

        Returns
        -------
        None

        """
        if self._buffer.icon_name != value:
            self._buffer.icon_name = value
            self.emit_paint_needed(0, 0, -1, -1)

    def get_icon_name(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        icon name :

        """
        return self._buffer.icon_name

    icon_name = gobject.property(
        type=object, getter=get_icon_name, setter=set_icon_name)

    def set_xo_color(self, value):
        """
        Parameters
        ----------
        value:

        Returns
        -------
        None

        """
        if self._buffer.xo_color != value:
            self._buffer.xo_color = value
            self._emit_paint_needed_icon_area()

    xo_color = gobject.property(
        type=object, getter=None, setter=set_xo_color)

    def set_fill_color(self, value):
        """
        Parameters
        ----------
        value:

        Returns
        -------
        None

        """
        if self._buffer.fill_color != value:
            self._buffer.fill_color = value
            self._emit_paint_needed_icon_area()

    def get_fill_color(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        fill color :

        """
        return self._buffer.fill_color

    fill_color = gobject.property(
        type=object, getter=get_fill_color, setter=set_fill_color)

    def set_stroke_color(self, value):
        """
        Parameters
        ----------
        value:

        Returns
        -------
        None

        """
        if self._buffer.stroke_color != value:
            self._buffer.stroke_color = value
            self._emit_paint_needed_icon_area()

    def get_stroke_color(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        stroke color :

        """
        return self._buffer.stroke_color

    stroke_color = gobject.property(
        type=object, getter=get_stroke_color, setter=set_stroke_color)

    def set_background_color(self, value):
        """
        Parameters
        ----------
        value:

        Returns
        -------
        None

        """
        if self._buffer.background_color != value:
            self._buffer.background_color = value
            self.emit_paint_needed(0, 0, -1, -1)

    def get_background_color(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        fill color :

        """
        return self._buffer.background_color

    background_color = gobject.property(
        type=object, getter=get_background_color, setter=set_background_color)

    def set_size(self, value):
        """
        Parameters
        ----------
        value:

        Returns
        -------
        None

        """
        if self._buffer.width != value:
            self._buffer.width = value
            self._buffer.height = value
            self.emit_request_changed()

    def get_size(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        size :

        """
        return self._buffer.width

    size = gobject.property(
        type=object, getter=get_size, setter=set_size)

    def set_scale(self, value):
        """
        Parameters
        ----------
        value:

        Returns
        -------
        None

        """
        logging.warning(
            'CanvasIcon: the scale parameter is currently unsupported')
        if self._buffer.scale != value:
            self._buffer.scale = value
            self.emit_request_changed()

    def get_scale(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        scale :

        """
        return self._buffer.scale

    scale = gobject.property(
        type=float, getter=get_scale, setter=set_scale)

    def set_cache(self, value):
        """
        Parameters
        ----------
        cache

        Returns
        -------
        None

        """
        self._buffer.cache = value

    def get_cache(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        cache :

        """
        return self._buffer.cache

    cache = gobject.property(
        type=bool, default=False, getter=get_cache, setter=set_cache)

    def set_badge_name(self, value):
        """
        Parameters
        ----------
        value :

        Returns
        -------
        None

        """
        if self._buffer.badge_name != value:
            self._buffer.badge_name = value
            self.emit_paint_needed(0, 0, -1, -1)

    def get_badge_name(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        badge name :

        """
        return self._buffer.badge_name

    badge_name = gobject.property(
        type=object, getter=get_badge_name, setter=set_badge_name)

    def do_paint_below_children(self, cr, damaged_box):
        """
        Parameters
        ----------
        cr :

        damaged_box :

        Returns
        -------
        None

        """
        surface = self._buffer.get_surface()
        if surface:
            width, height = self.get_allocation()

            x = (width - surface.get_width()) / 2
            y = (height - surface.get_height()) / 2

            cr.set_source_surface(surface, x, y)
            cr.paint()

    def do_get_content_width_request(self):
        """
        Parameters
        ----------
        None

        Returns
        -------
        width :

        """
        surface = self._buffer.get_surface()
        if surface:
            size = surface.get_width()
        elif self._buffer.width:
            size = self._buffer.width
        else:
            size = 0

        return size, size

    def do_get_content_height_request(self, for_width):
        surface = self._buffer.get_surface()
        if surface:
            size = surface.get_height()
        elif self._buffer.height:
            size = self._buffer.height
        else:
            size = 0

        return size, size

    def do_button_press_event(self, event):
        if event.button == 1:
            self.emit_activated()
            return True
        else:
            return False

    def create_palette(self):
        return None

    def get_palette(self):
        return self._palette_invoker.palette

    def set_palette(self, palette):
        self._palette_invoker.palette = palette

    palette = gobject.property(
        type=object, setter=set_palette, getter=get_palette)

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = gobject.property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker)

    def set_tooltip(self, text):
        from sugar.graphics.palette import Palette

        self.set_palette(Palette(text))


class CellRendererIcon(gtk.GenericCellRenderer):

    __gtype_name__ = 'SugarCellRendererIcon'

    __gsignals__ = {
        'clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, [object]),
    }

    def __init__(self, tree_view):
        from sugar.graphics.palette import CellRendererInvoker

        self._buffer = _IconBuffer()
        self._buffer.cache = True
        self._xo_color = None
        self._fill_color = None
        self._stroke_color = None
        self._prelit_fill_color = None
        self._prelit_stroke_color = None
        self._palette_invoker = CellRendererInvoker()

        gobject.GObject.__init__(self)

        self._palette_invoker.attach_cell_renderer(tree_view, self)

        self.connect('destroy', self.__destroy_cb)

    def __destroy_cb(self, icon):
        self._palette_invoker.detach()

    def create_palette(self):
        return None

    def get_palette_invoker(self):
        return self._palette_invoker

    palette_invoker = gobject.property(type=object, getter=get_palette_invoker)

    def set_file_name(self, value):
        if self._buffer.file_name != value:
            self._buffer.file_name = value

    file_name = gobject.property(type=str, setter=set_file_name)

    def set_icon_name(self, value):
        if self._buffer.icon_name != value:
            self._buffer.icon_name = value

    icon_name = gobject.property(type=str, setter=set_icon_name)

    def get_xo_color(self):
        return self._xo_color

    def set_xo_color(self, value):
        self._xo_color = value

    xo_color = gobject.property(type=object,
            getter=get_xo_color, setter=set_xo_color)

    def set_fill_color(self, value):
        if self._fill_color != value:
            self._fill_color = value

    fill_color = gobject.property(type=object, setter=set_fill_color)

    def set_stroke_color(self, value):
        if self._stroke_color != value:
            self._stroke_color = value

    stroke_color = gobject.property(type=object, setter=set_stroke_color)

    def set_prelit_fill_color(self, value):
        if self._prelit_fill_color != value:
            self._prelit_fill_color = value

    prelit_fill_color = gobject.property(type=object,
                                         setter=set_prelit_fill_color)

    def set_prelit_stroke_color(self, value):
        if self._prelit_stroke_color != value:
            self._prelit_stroke_color = value

    prelit_stroke_color = gobject.property(type=object,
                                           setter=set_prelit_stroke_color)

    def set_background_color(self, value):
        if self._buffer.background_color != value:
            self._buffer.background_color = value

    background_color = gobject.property(type=object,
                                        setter=set_background_color)

    def set_size(self, value):
        if self._buffer.width != value:
            self._buffer.width = value
            self._buffer.height = value

    size = gobject.property(type=object, setter=set_size)

    def on_get_size(self, widget, cell_area):
        width = self._buffer.width + self.props.xpad * 2
        height = self._buffer.height + self.props.ypad * 2
        xoffset = 0
        yoffset = 0

        if width > 0 and height > 0 and cell_area is not None:

            if widget.get_direction() == gtk.TEXT_DIR_RTL:
                xoffset = 1.0 - self.props.xalign
            else:
                xoffset = self.props.xalign

            xoffset = max(xoffset * (cell_area.width - width), 0)
            yoffset = max(self.props.yalign * (cell_area.height - height), 0)

        return xoffset, yoffset, width, height

    def on_activate(self, event, widget, path, background_area, cell_area,
                    flags):
        pass

    def on_start_editing(self, event, widget, path, background_area, cell_area,
                         flags):
        pass

    def _is_prelit(self, tree_view):
        x, y = tree_view.get_pointer()
        x, y = tree_view.convert_widget_to_bin_window_coords(x, y)
        pos = tree_view.get_path_at_pos(x, y)
        if pos is None:
            return False

        path_, column, x, y = pos

        for cell_renderer in column.get_cell_renderers():
            if cell_renderer == self:
                cell_x, cell_width = column.cell_get_position(cell_renderer)
                if x > cell_x and x < (cell_x + cell_width):
                    return True
                return False

        return False

    def on_render(self, window, widget, background_area, cell_area,
            expose_area, flags):
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

        if flags & gtk.CELL_RENDERER_PRELIT and has_prelit_colors and \
                self._is_prelit(widget):

            self._buffer.fill_color = prelit_fill_color
            self._buffer.stroke_color = prelit_stroke_color
        else:
            self._buffer.fill_color = fill_color
            self._buffer.stroke_color = stroke_color

        surface = self._buffer.get_surface()
        if surface is None:
            return

        xoffset, yoffset, width_, height_ = self.on_get_size(widget, cell_area)

        x = cell_area.x + xoffset
        y = cell_area.y + yoffset

        cr = window.cairo_create()
        cr.set_source_surface(surface, math.floor(x), math.floor(y))
        cr.rectangle(expose_area)
        cr.paint()


def get_icon_state(base_name, perc, step=5):
    strength = round(perc / step) * step
    icon_theme = gtk.icon_theme_get_default()

    while strength <= 100 and strength >= 0:
        icon_name = '%s-%03d' % (base_name, strength)
        if icon_theme.has_icon(icon_name):
            return icon_name

        strength = strength + step


def get_icon_file_name(icon_name):
    icon_theme = gtk.icon_theme_get_default()
    info = icon_theme.lookup_icon(icon_name, gtk.ICON_SIZE_LARGE_TOOLBAR, 0)
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

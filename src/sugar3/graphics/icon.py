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

'''
Icons are small pictures that are used to decorate components.  In Sugar, icons
are SVG files that are re-coloured with a fill and a stroke colour.  Typically,
icons representing the system use a greyscale color palette, whereas icons
representing people take on their selected XoColors.

Designing a Sugar Icon
======================

If you want to make an icon to use in Sugar, start by designing something in
a vector program, like Inkscape.  When you are designing the icon, use a canvas
that is 55x55px.

When designing your icon, use 2 colors.  For example, use a black stroke and a
white fill color.  You need to keep this consistent and remember those colors.

You should also keep the subcell grid in mind when designing the icon.  A grid
cell (which the size of an icon) is made up of 5 by 5 subcells.  To use this in
Inkscape, enable the page grid (View -> Page Grid), the go to grid properties
(File -> Document Properties -> Grids).  In grid properties, set the "Spacing
X" option to 11, "Spacing Y" to 11 and "Major grid line every" to 1.

Before your icon is ready to be used in Sugar, it needs to be Sugarized.  This
converts the colors to SVG entities, which allows Sugar to change the colors
of the icon.  To do that, just run the `sugar-iconify`__ script.  Usually, it
"just works" like::

    python path/to/sugar-iconify.py -o icon.svg

__ https://github.com/GhostAlgorithm/sugariconify/blob/master/sugariconify.py

Code Example
============

Example of using icons with badges:

.. literalinclude:: ../examples/iconbadges.py

Badge Icons
===========
Badge icons are small icons that are attached to the normal icon.
For example, a WiFi network icon might have a star badge attached to
the bottom left corner (the "attach point") that indicates that the
network is connected to.

Badge icons are displayed at _BADGE_SIZE percent (45% currently),
of their main icon.

Badge icons are specified by the icon name, in the same sense that
normal icons have a :any:`Icon.set_icon_name` function.

Attach Points
-------------

Where the badge icon is placed is defined by the main icon.  By
default, it is centered on 0, 0.  That means that the 3 quarters of
the icon will be cut off!  Therefore, it is helpful to define the
attach points.

When Sugar loads the main icon, it looks for a `.icon` file.  For
example, if the icon path is resolved to `/theme/computer-xo.svg`,
the `/theme/computer-xo.icon` will be tried to find the attach points.

The `.icon` files are to be formatted as follows::

    [Icon Data]
    AttachPoints=970,850

In this example, the badge will be centered at 97.0% on the X axis,
and 85.0% on the Y axis.
'''

import six
import re
import math
import logging
import os

from six.moves.configparser import ConfigParser

import gi
gi.require_version('Rsvg', '2.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GLib
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
        self._cache = LRU(100)

    def load(self, file_name, entities, cache):
        if file_name in self._cache:
            icon = self._cache[file_name]
        else:
            icon_file = open(file_name, 'r')
            icon = icon_file.read()
            icon_file.close()

            if cache:
                self._cache[file_name] = icon

        for entity, value in list(entities.items()):
            if isinstance(value, six.string_types):
                xml = '<!ENTITY %s "%s">' % (entity, value)
                icon = re.sub('<!ENTITY %s .*>' % entity, xml, icon)
            else:
                logging.error(
                    'Icon %s, entity %s is invalid.', file_name, entity)

        return Rsvg.Handle.new_from_data(icon.encode('utf-8'))


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

    _surface_cache = LRU(100)
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
        self.pixbuf = None

    def _get_cache_key(self, sensitive):
        if self.background_color is None:
            color = None
        else:
            color = (self.background_color.red, self.background_color.green,
                     self.background_color.blue)

        return (self.icon_name, self.file_name, self.pixbuf, self.fill_color,
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
        attach_x = attach_y = 0
        if attach_points:
            # this works only for Gtk < 3.14
            # https://developer.gnome.org/gtk3/stable/GtkIconTheme.html
            # #gtk-icon-info-get-attach-points
            attach_x = float(attach_points[0].x) / size_request
            attach_y = float(attach_points[0].y) / size_request
        elif info.get_filename():
            # try read from the .icon file
            icon_filename = info.get_filename().replace('.svg', '.icon')
            if icon_filename != info.get_filename() and \
                    os.path.exists(icon_filename):

                try:
                    with open(icon_filename) as config_file:
                        cp = ConfigParser()
                        cp.readfp(config_file)
                        attach_points_str = cp.get('Icon Data', 'AttachPoints')
                        attach_points = attach_points_str.split(',')
                        attach_x = float(attach_points[0].strip()) / 1000
                        attach_y = float(attach_points[1].strip()) / 1000
                except Exception as e:
                    logging.exception('Exception reading icon info: %s', e)

        return attach_x, attach_y

    def _get_icon_info(self, file_name, icon_name):
        icon_info = _IconInfo()

        if file_name:
            icon_info.file_name = file_name
        elif icon_name:
            theme = Gtk.IconTheme.get_default()

            size = 50
            if self.width is not None:
                size = self.width

            info = theme.lookup_icon(icon_name, int(size), 0)
            if info:
                attach_x, attach_y = self._get_attach_points(info, size)

                icon_info.file_name = info.get_filename()
                icon_info.attach_x = attach_x
                icon_info.attach_y = attach_y

                del info
            else:
                logging.warning('No icon with the name %s was found in the '
                                'theme.', icon_name)

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

        widget_style = widget.get_style()
        pixbuf = widget_style.render_icon(
            icon_source, widget.get_direction(),
            Gtk.StateType.INSENSITIVE, -1, widget,
            'sugar-icon')

        return pixbuf

    def get_surface(self, sensitive=True, widget=None):
        cache_key = self._get_cache_key(sensitive)
        if cache_key in self._surface_cache:
            return self._surface_cache[cache_key]

        if self.pixbuf:
            # We alredy have the pixbuf for this icon.
            pixbuf = self.pixbuf
            icon_width = pixbuf.get_width()
            icon_height = pixbuf.get_height()
            icon_info = self._get_icon_info(self.file_name, self.icon_name)
            is_svg = False
        else:
            # We run two attempts at finding the icon. First, we try the icon
            # requested by the user. If that fails, we fall back on
            # document-generic. If that doesn't work out, bail.
            icon_width = None
            for (file_name, icon_name) in ((self.file_name, self.icon_name),
                                           (None, 'document-generic')):
                icon_info = self._get_icon_info(file_name, icon_name)
                if icon_info.file_name is None:
                    return None

                is_svg = icon_info.file_name.endswith('.svg')

                if is_svg:
                    try:
                        handle = self._load_svg(icon_info.file_name)
                        icon_width = handle.props.width
                        icon_height = handle.props.height
                        break
                    except IOError:
                        pass
                else:
                    try:
                        path = icon_info.file_name
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
                        icon_width = pixbuf.get_width()
                        icon_height = pixbuf.get_height()
                        break
                    except GLib.GError:
                        pass

        if icon_width is None:
            # Neither attempt found an icon for us to use
            return None

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
    '''
    The most basic Sugar icon class.  Displays the icon given.

    You must set either the `file_name`, `file` or `icon_name` properties,
    otherwise, no icon will be visible.

    You should set the `pixel_size`, using constants the `*_ICON_SIZE`
    constants from :any:`sugar3.graphics.style`.

    You should set the color (either via `xo_color` or `fill_color` and
    `stroke_color`), otherwise the default black and white fill and stroke
    will be used.

    Keyword Args:
        file_name (str): a path to the SVG icon file
        file (object): same behaviour as file_name, but for
            :class:`sugar3.util.TempFilePath` type objects
        icon_name (str): a name of an icon in the theme to display.  The
            icons in the theme include those in the sugar-artwork project
            and icons in the activity's '/icons' directory
        pixel_size (int): size of the icon, in pixels.  Best to use the
            constants from :class:`sugar3.graphics.style`, as those constants
            are scaled based on the user's preferences
        xo_color (sugar3.graphics.xocolor.XoColor): color to display icon,
            a shortcut that just sets the fill_color and stroke_color
        fill_color (str): a string, like '#FFFFFF', that will serve as the
            fill color for the icon
        stroke_color (str): a string, like '#282828', that will serve as the
            stroke color for the icon
        icon_size: deprecated since 0.102.0, use pixel_size instead
        badge_name (str): the icon_name for a badge icon,
            see :any:`set_badge_name`
        alpha (float): transparency of the icon, defaults to 1.0
    '''

    __gtype_name__ = 'SugarIcon'

    _MENU_SIZES = (Gtk.IconSize.MENU, Gtk.IconSize.DND,
                   Gtk.IconSize.SMALL_TOOLBAR, Gtk.IconSize.BUTTON)

    def __init__(self, **kwargs):
        self._buffer = _IconBuffer()
        # HACK: need to keep a reference to the path so it doesn't get garbage
        # collected while it's still used if it's a sugar3.util.TempFilePath.
        # See #1175
        self._file = None
        self._alpha = 1.0
        self._scale = 1.0

        if 'icon_size' in kwargs:
            logging.warning("icon_size is deprecated. Use pixel_size instead.")

        GObject.GObject.__init__(self, **kwargs)

    def get_file(self):
        return self._file

    def set_file(self, file_name):
        self._file = file_name
        self._buffer.file_name = file_name

    file = GObject.Property(type=object, setter=set_file, getter=get_file)

    def get_pixbuf(self):
        '''
        Returns the :class:`GdkPixbuf.Pixbuf` for the icon, if one has been
        loaded yet.  If the icon has been drawn (:any:`do_draw`), the icon
        will be loaded.

        The pixbuf only contains the SVG icon that has been loaded and
        recoloured.  It does not contain the badge.
        '''
        return self._buffer.pixbuf

    def set_pixbuf(self, pixbuf):
        '''
        Set the pixbuf.  This will force the icon to be rendered with the
        given pixbuf.  The icon will still be centered, badge added, etc.

        Args:
            pixbuf (GdkPixbuf.Pixbuf): pixbuf to set
        '''
        self._buffer.pixbuf = pixbuf

    pixbuf = GObject.Property(type=object, setter=set_pixbuf,
                              getter=get_pixbuf)
    '''
    icon.props.pixbuf -> see :any:`get_pixbuf` and :any:`set_pixbuf`
    '''

    def _sync_image_properties(self):
        if self._buffer.icon_name != self.props.icon_name:
            self._buffer.icon_name = self.props.icon_name

        if self._buffer.file_name != self.props.file:
            self._buffer.file_name = self.props.file

        pixel_size = None
        if self.props.pixel_size == -1:
            if self.props.icon_size in self._MENU_SIZES:
                pixel_size = style.SMALL_ICON_SIZE
            else:
                pixel_size = style.STANDARD_ICON_SIZE
        else:
            pixel_size = self.props.pixel_size

        width = height = pixel_size

        if self._buffer.width != width or self._buffer.height != height:
            self._buffer.width = width
            self._buffer.height = height

    def _icon_size_changed_cb(self, image, pspec):
        self._buffer.icon_size = self.props.pixel_size

    def _icon_name_changed_cb(self, image, pspec):
        self._buffer.icon_name = self.props.icon_name

    def _file_changed_cb(self, image, pspec):
        self._buffer.file_name = self.props.file

    def do_get_preferred_height(self):
        '''Gtk widget implementation method'''
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
        '''Gtk widget implementation method'''
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
        '''Gtk widget implementation method'''
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
        '''
        Set the colors used to display the icon

        Args:
            value (sugar3.graphics.xocolor.XoColor): new XoColor to use
        '''
        if self._buffer.xo_color != value:
            self._buffer.xo_color = value
            self.queue_draw()

    xo_color = GObject.Property(
        type=object, getter=None, setter=set_xo_color)
    '''
    icon.props.xo_color -> see :any:`set_xo_color`, note there is no getter
    '''

    def set_fill_color(self, value):
        '''
        Set the color used to fill the icon

        Args:
            value (str): SVG color string, like '#FFFFFF'
        '''
        if self._buffer.fill_color != value:
            self._buffer.fill_color = value
            self.queue_draw()

    def get_fill_color(self):
        '''
        Get the color used to fill the icon

        Returns:
            str, SVG color string, like '#FFFFFF'
        '''
        return self._buffer.fill_color

    fill_color = GObject.Property(
        type=object, getter=get_fill_color, setter=set_fill_color)
    '''
    icon.props.fill_color -> see :any:`get_fill_color`
        and :any:`set_fill_color`
    '''

    def set_stroke_color(self, value):
        '''
        Set the color used to paint the icon stroke

        Args:
            value (str): SVG color string, like '#282828'
        '''
        if self._buffer.stroke_color != value:
            self._buffer.stroke_color = value
            self.queue_draw()

    def get_stroke_color(self):
        '''
        Get the color used to paint the icon stroke

        Returns:
            str, SVG color string, like '#282828'
        '''
        return self._buffer.stroke_color

    stroke_color = GObject.Property(
        type=object, getter=get_stroke_color, setter=set_stroke_color)
    '''
    icon.props.stroke_color -> see :any:`get_stroke_color`
        and :any:`set_stroke_color`
    '''

    def set_badge_name(self, value):
        '''
        See the Badge Icons section at the top of the file.

        Args:
            value (str): the icon name for the badge
        '''
        if self._buffer.badge_name != value:
            self._buffer.badge_name = value
            self.queue_resize()

    def get_badge_name(self):
        '''
        Get the badge name, as set by :any:`set_badge_name`

        Returns:
            str, badge icon name
        '''
        return self._buffer.badge_name

    badge_name = GObject.Property(
        type=str, getter=get_badge_name, setter=set_badge_name)
    '''
    icon.props.badge_name -> see :any:`get_badge_name`
        and :any:`set_badge_name`
    '''

    def get_badge_size(self):
        '''
        Returns:
            int, size of badge icon, in pixels
        '''
        return int(_BADGE_SIZE * self.props.pixel_size)

    def set_alpha(self, value):
        '''
        Set the transparency for the icon.  Defaults to 1.0, which is
        fully visible icon.

        Args:
            value (float): alpha value from 0.0 to 1.0
        '''
        if self._alpha != value:
            self._alpha = value
            self.queue_draw()

    alpha = GObject.Property(
        type=float, setter=set_alpha)
    '''
    icon.props.alpha -> see :any:`set_alpha`, note no getter
    '''

    def set_scale(self, value):
        '''
        Scales the icon, with the transformation origin at the top left
        corner.  Note that this only scales the resulting drawing, so
        at large scales the icon will appear pixilated.

        Args:
            value (float): new scaling factor
        '''
        if self._scale != value:
            self._scale = value
            self.queue_draw()

    scale = GObject.Property(
        type=float, setter=set_scale)
    '''
    icon.props.scale -> see :any:`set_scale`, note no getter
    '''


class EventIcon(Gtk.EventBox):
    '''
    An Icon class that provides access to mouse events and that can act as a
    cursor-positioned palette invoker.

    The palette invoker can be used in 3 ways:

    1.  Set the palette during your constructor, see :any:`set_palette`
    2.  Override the create_palette method, see :any:`create_palette`
    3.  Set the tooltip, see :any:`create_tooltip`

    Otherwise, the icon setup api is the same as the basic :class:`Icon`.
    This EventIcon class supports the icon_name, stroke_color, fill_color,
    file_name, xo_color, pixel_size, scale and alpha keyword arguments as
    the :class:`Icon`.  The added arguments are as follows:

    Keyword Args:
        background_color (Gdk.Color): the color to draw the icon on top of.
            It defaults to None, which means no background is drawn
            (transparent).  The alpha channel of the Gdk.Color is disregarded.
        cache (bool): if True, the icon file contents will be cached to
            reduce disk usage
        palette (sugar3.graphics.palette.Palette): a palette to connect
    '''

    __gsignals__ = {
        'activate': (GObject.SignalFlags.RUN_FIRST, None, []),
    }

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
        # Connect after the default so that the palette can silence events
        # for example, after a touch palette invocation
        self.connect_after('button-release-event',
                           self.__button_release_event_cb)
        for key, value in six.iteritems(kwargs):
            self.set_property(key, value)

        from sugar3.graphics.palette import CursorInvoker
        self._palette_invoker = CursorInvoker()
        self._palette_invoker.attach(self)
        self.connect('destroy', self.__destroy_cb)

    def do_draw(self, cr):
        '''Gtk widget implementation method'''
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
        '''Gtk widget implementation method'''
        surface = self._buffer.get_surface()
        if surface:
            height = surface.get_height()
        elif self._buffer.height:
            height = self._buffer.height
        else:
            height = 0
        return (height, height)

    def do_get_preferred_width(self):
        '''Gtk widget implementation method'''
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

    file_name = GObject.Property(
        type=object, getter=get_file_name, setter=set_file_name)

    def set_icon_name(self, value):
        if self._buffer.icon_name != value:
            self._buffer.icon_name = value
            self.queue_draw()

    def get_icon_name(self):
        return self._buffer.icon_name

    icon_name = GObject.Property(
        type=object, getter=get_icon_name, setter=set_icon_name)

    def set_xo_color(self, value):
        if self._buffer.xo_color != value:
            self._buffer.xo_color = value
            self.queue_draw()

    xo_color = GObject.Property(
        type=object, getter=None, setter=set_xo_color)

    def set_fill_color(self, value):
        if self._buffer.fill_color != value:
            self._buffer.fill_color = value
            self.queue_draw()

    def get_fill_color(self):
        return self._buffer.fill_color

    fill_color = GObject.Property(
        type=object, getter=get_fill_color, setter=set_fill_color)

    def set_stroke_color(self, value):
        if self._buffer.stroke_color != value:
            self._buffer.stroke_color = value
            self.queue_draw()

    def get_stroke_color(self):
        return self._buffer.stroke_color

    stroke_color = GObject.Property(
        type=object, getter=get_stroke_color, setter=set_stroke_color)

    def set_background_color(self, value):
        '''
        Args:
            value (Gdk.Color): color use as background (alpha is ignored),
                or None meaning no background is drawn (transparent)
        '''
        if self._buffer.background_color != value:
            self._buffer.background_color = value
            self.queue_draw()

    def get_background_color(self):
        '''
        Returns:
            Gdk.Color, current background color, may be None
        '''
        return self._buffer.background_color

    background_color = GObject.Property(
        type=object, getter=get_background_color, setter=set_background_color)
    '''
    event_icon.props.get_background_color -> see :any:`set_background_color`
        and :any:`get_background_color`
    '''

    def set_size(self, value):
        if self._buffer.width != value:
            self._buffer.width = value
            self._buffer.height = value
            self.queue_resize()

    def get_size(self):
        return self._buffer.width

    pixel_size = GObject.Property(
        type=object, getter=get_size, setter=set_size)

    def set_scale(self, value):
        if self._buffer.scale != value:
            self._buffer.scale = value
            self.queue_resize()

    def get_scale(self):
        return self._buffer.scale

    scale = GObject.Property(
        type=float, getter=get_scale, setter=set_scale)

    def set_alpha(self, alpha):
        if self._alpha != alpha:
            self._alpha = alpha
            self.queue_draw()

    alpha = GObject.Property(
        type=float, setter=set_alpha)

    def set_cache(self, value):
        '''
        Sugar caches icon file contents in a smart cache.  Currently, we use
        a LRU (Least Recently Used) algorithm to manage the cache.

        Args:
            value (bool): if True, the icon file will be cached in the LRU
        '''
        self._buffer.cache = value

    def get_cache(self):
        '''
        Returns:
            bool, if the icon file will be saved in the LRU
        '''
        return self._buffer.cache

    cache = GObject.Property(
        type=bool, default=False, getter=get_cache, setter=set_cache)
    '''
    event_icon.props.cache -> see :any:`set_cache` and :any:`get_cache`
    '''

    def set_badge_name(self, value):
        if self._buffer.badge_name != value:
            self._buffer.badge_name = value
            self.queue_draw()

    def get_badge_name(self):
        return self._buffer.badge_name

    badge_name = GObject.Property(
        type=object, getter=get_badge_name, setter=set_badge_name)

    def create_palette(self):
        '''
        The create_palette function is called when the palette needs to be
        invoked.  For example, when the user has right clicked the icon or
        the user has hovered over the icon for a long time.

        The create_palette will only be called once or zero times.  The palette
        returned will be stored and re-used if the user invokes the palette
        multiple times.

        Your create_palette implementation does not need to
        :any:`Gtk.Widget.show` the palette, as this will be done by the
        invoker.  However, you still need to show
        the menu items, etc that you place in the palette.

        Returns:
            sugar3.graphics.palette.Palette, or None to indicate that you
            do not want a palette shown

        The default implementation returns None, to indicate no palette should
        be shown.
        '''
        return None

    def get_palette(self):
        '''
        Gets the current palette, either set by :any:`set_palette` or cached
        after a call to :any:`create_palette`
        '''
        return self._palette_invoker.palette

    def set_palette(self, palette):
        '''
        Sets the palette to show.  If the palette is not None, this will
        override the palette set by create_palette.

        Args:
            palette (sugar3.graphics.palette.Palette): palette or None
        '''
        self._palette_invoker.palette = palette

    palette = GObject.Property(
        type=object, setter=set_palette, getter=get_palette)
    '''
    event_icon.props.palette -> see :any:`get_palette` and :any:`set_palette`
    '''

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = GObject.Property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker)

    def set_tooltip(self, text):
        '''
        Creates a palette with the tooltip text.  This will override any
        current palette set through :any:`set_palette` or that will ever be
        returned by :any:`create_palette`.

        Args:
            text (str): tooltip text
        '''
        from sugar3.graphics.palette import Palette

        self.set_palette(Palette(text))

    def __button_release_event_cb(self, icon, event):
        if event.button == 1:
            alloc = self.get_allocation()
            if 0 < event.x < alloc.width and 0 < event.y < alloc.height:
                self.emit('activate')


class CanvasIcon(EventIcon):
    '''
    An EventIcon with active and prelight states, and a styleable
    background.  If the icon pops up a palette, the prelight state is
    set until the palette pops down.  This is used to render a light
    grey highlight, however can be configured by Gtk+ CSS with the
    `:prelight` selector.

    Care should to use :any:`connect_to_palette_pop_events` for all palettes
    created and shown around this icon.
    '''

    __gtype_name__ = 'SugarCanvasIcon'

    def __init__(self, **kwargs):
        EventIcon.__init__(self, **kwargs)
        self._button_down = False

        self.connect('enter-notify-event', self.__enter_notify_event_cb)
        self.connect('leave-notify-event', self.__leave_notify_event_cb)
        self.connect('button-press-event', self.__button_press_event_cb)
        self.connect('button-release-event', self.__button_release_event_cb)

    def connect_to_palette_pop_events(self, palette):
        '''
        Connect to the palette's popup and popdown events, so that the prelight
        state is set at the right times.  You should run this call
        before you :any:`EventIcon.set_palette` or before you return from
        your :any:`EventIcon.create_palette` function, eg:

            def create_palette(self):
                palette = ...

                self.connect_to_palette_pop_events(palette)
                return palette

        Args:
            palette (sugar3.graphics.palette.Palette): palette to connect
        '''
        palette.connect('popup', self.__palette_popup_cb)
        palette.connect('popdown', self.__palette_popdown_cb)

    def do_draw(self, cr):
        '''Gtk widget implementation method'''
        allocation = self.get_allocation()
        context = self.get_style_context()
        Gtk.render_background(context, cr, 0, 0,
                              allocation.width,
                              allocation.height)

        EventIcon.do_draw(self, cr)

    def __enter_notify_event_cb(self, icon, event):
        self.set_state_flags(self.get_state_flags() | Gtk.StateFlags.PRELIGHT,
                             clear=True)
        if self._button_down:
            self.set_state_flags(Gtk.StateFlags.ACTIVE, clear=False)

    def __leave_notify_event_cb(self, icon, event):
        if self.palette and self.palette.is_up():
            return

        self.unset_state_flags(Gtk.StateFlags.PRELIGHT | Gtk.StateFlags.ACTIVE)

    def __button_press_event_cb(self, icon, event):
        if self.palette and not self.palette.is_up():
            self._button_down = True
            self.set_state_flags(
                self.get_state_flags() | Gtk.StateFlags.ACTIVE,
                clear=True)

    def __button_release_event_cb(self, icon, event):
        self.unset_state_flags(Gtk.StateFlags.ACTIVE)
        self._button_down = False

    def __palette_popup_cb(self, palette):
        self.set_state_flags(Gtk.StateFlags.PRELIGHT, clear=True)

    def __palette_popdown_cb(self, palette):
        self.unset_state_flags(Gtk.StateFlags.PRELIGHT)


if hasattr(CanvasIcon, 'set_css_name'):
    CanvasIcon.set_css_name('canvasicon')


class CellRendererIcon(Gtk.CellRenderer):

    __gtype_name__ = 'SugarCellRendererIcon'

    __gsignals__ = {
        'clicked': (GObject.SignalFlags.RUN_FIRST, None, [object]),
    }

    def __init__(self, treeview=None):
        # treeview is not used anymore, is here just to not break the API
        if treeview is not None:
            logging.warning('CellRendererIcon: treeview parameter in '
                            'constructor is deprecated')
        self._buffer = _IconBuffer()
        self._buffer.cache = True
        self._xo_color = None
        self._fill_color = None
        self._stroke_color = None
        self._prelit_fill_color = None
        self._prelit_stroke_color = None
        self._active_state = False
        self._cached_offsets = None

        Gtk.CellRenderer.__init__(self)

        self._is_scrolling = False

    def connect_to_scroller(self, scrolled):
        scrolled.connect('scroll-start', self._scroll_start_cb)
        scrolled.connect('scroll-end', self._scroll_end_cb)

    def _scroll_start_cb(self, event):
        self._is_scrolling = True

    def _scroll_end_cb(self, event):
        self._is_scrolling = False

    def is_scrolling(self):
        return self._is_scrolling

    def create_palette(self):
        return None

    def set_file_name(self, value):
        if self._buffer.file_name != value:
            self._buffer.file_name = value

    file_name = GObject.Property(type=str, setter=set_file_name)

    def set_icon_name(self, value):
        if self._buffer.icon_name != value:
            self._buffer.icon_name = value

    icon_name = GObject.Property(type=str, setter=set_icon_name)

    def get_xo_color(self):
        return self._xo_color

    def set_xo_color(self, value):
        self._xo_color = value

    xo_color = GObject.Property(type=object,
                                getter=get_xo_color, setter=set_xo_color)

    def set_fill_color(self, value):
        if self._fill_color != value:
            self._fill_color = value

    fill_color = GObject.Property(type=object, setter=set_fill_color)

    def set_stroke_color(self, value):
        if self._stroke_color != value:
            self._stroke_color = value

    stroke_color = GObject.Property(type=object, setter=set_stroke_color)

    def set_prelit_fill_color(self, value):
        if self._prelit_fill_color != value:
            self._prelit_fill_color = value

    prelit_fill_color = GObject.Property(type=object,
                                         setter=set_prelit_fill_color)

    def set_prelit_stroke_color(self, value):
        if self._prelit_stroke_color != value:
            self._prelit_stroke_color = value

    prelit_stroke_color = GObject.Property(type=object,
                                           setter=set_prelit_stroke_color)

    def set_background_color(self, value):
        if self._buffer.background_color != value:
            self._buffer.background_color = value

    background_color = GObject.Property(type=object,
                                        setter=set_background_color)

    def set_size(self, value):
        if self._buffer.width != value:
            self._buffer.width = value
            self._buffer.height = value

            self._cached_offsets = None

    size = GObject.Property(type=object, setter=set_size)

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
            self._cached_offsets = xoffset, yoffset

        return xoffset, yoffset, width, height

    def _get_offsets(self, widget, cell_area):
        if self._cached_offsets is not None:
            return self._cached_offsets

        xoffset, yoffset, width_, height_ = self.do_get_size(widget, cell_area)
        return xoffset, yoffset

    def do_activate(self, event, widget, path, background_area, cell_area,
                    flags):
        pass

    def do_start_editing(self, event, widget, path, background_area, cell_area,
                         flags):
        pass

    def do_render(self, cr, widget, background_area, cell_area, flags):
        if not self._is_scrolling:

            context = widget.get_style_context()
            context.save()
            context.add_class("sugar-icon-cell")

            def is_pointer_inside():
                # widget is the treeview
                x, y = widget.get_pointer()
                x, y = widget.convert_widget_to_bin_window_coords(x, y)
                return ((cell_area.x <= x <= cell_area.x + cell_area.width) and
                        (cell_area.y <= y <= cell_area.y + cell_area.height))

            pointer_inside = is_pointer_inside()

            # The context will have prelight state if the mouse pointer is
            # in the entire row, but we want that state if the pointer is
            # in this cell only:
            if flags & Gtk.CellRendererState.PRELIT:
                if pointer_inside:
                    if self._active_state:
                        context.set_state(Gtk.StateFlags.ACTIVE)
                else:
                    context.set_state(Gtk.StateFlags.NORMAL)

            Gtk.render_background(
                context, cr, background_area.x, background_area.y,
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
        else:
            if self._xo_color is not None:
                self._buffer.fill_color = self._xo_color.get_fill_color()
                self._buffer.stroke_color = self._xo_color.get_stroke_color()
            else:
                self._buffer.fill_color = self._fill_color
                self._buffer.stroke_color = self._stroke_color

        surface = self._buffer.get_surface()
        if surface is None:
            return

        xoffset, yoffset = self._get_offsets(widget, cell_area)

        x = cell_area.x + xoffset
        y = cell_area.y + yoffset

        cr.set_source_surface(surface, math.floor(x), math.floor(y))
        cr.rectangle(cell_area.x, cell_area.y, cell_area.width,
                     cell_area.height)
        cr.clip()
        cr.paint()


def get_icon_state(base_name, perc, step=5):
    '''
    Get the closest icon name for a given state in percent.

    First, you need a set of icons. They must be prefixed with `base_name`,
    for example "network-wireless". They must be suffixed with 3 digit
    percentage numbers, for example "-000", "-200", etc. Eventually, you get
    a collection of icon names like:

    * network-wireless-000
    * network-wireless-020
    * network-wireless-040
    * network-wireless-060
    * network-wireless-080
    * network-wireless-100

    All of these icons must be placed in the icon theme, such that they are
    addressable by their `icon_name`.

    Args:
        base_name (str): base icon name, eg `network-wireless`
        perc (float): desired percentage between 0 and 100, eg. 67.8

    Keyword Arguments:
        step (int): step to increment to find all possible icons

            From the example above, we could step 5, because 0, 5, 10, 15, etc,
            includes all number suffixes in our set of icons (0, 20, 40, etc).

            If we had the number suffixes 0, 33, 66, 99, we could not use 5,
            as none of the numbers are divisible by 5.

    Returns:
        str, icon name that represent given state, or None if not found
    '''
    strength = round(perc / step) * step
    icon_theme = Gtk.IconTheme.get_default()

    while strength <= 100 and strength >= 0:
        icon_name = '%s-%03d' % (base_name, strength)
        if icon_theme.has_icon(icon_name):
            return icon_name

        strength = strength + step


def get_icon_file_name(icon_name):
    '''
    Resolves a given icon name into a file path.  Looks for any icon in them
    theme, including those in sugar-artwork and those in the activities
    '/icons/' directory.

    Returns:
        str, path to icon, or None is the icon is not found in the theme
    '''
    icon_theme = Gtk.IconTheme.get_default()
    info = icon_theme.lookup_icon(icon_name, Gtk.IconSize.LARGE_TOOLBAR, 0)
    if not info:
        return None
    filename = info.get_filename()
    del info
    return filename


def get_surface(**kwargs):
    '''
    Get cairo surface of the icon.  Supports the same arguments as
    :any:`Icon`, in exactly the same way.

    Returns:
        cairo surface or None if image was not found
    '''
    icon = _IconBuffer()
    for key, value in list(kwargs.items()):
        icon.__setattr__(key, value)
    return icon.get_surface()

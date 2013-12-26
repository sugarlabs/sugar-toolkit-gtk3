# Copyright (C) 2007, Red Hat, Inc.
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
All the constants are expressed in pixels. They are defined for the XO screen
and are usually adapted to different resolution by applying a zoom factor.

STABLE.
"""

import os
import logging

from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import Gio


FOCUS_LINE_WIDTH = 2
_TAB_CURVATURE = 1


def _compute_zoom_factor():
    try:
        scaling = int(os.environ.get('SUGAR_SCALING', '100'))
        return scaling / 100.0
    except ValueError:
        logging.error('Invalid SUGAR_SCALING.')

    return 1.0


class Font(object):

    def __init__(self, desc):
        self._desc = desc

    def __str__(self):
        return self._desc

    def get_pango_desc(self):
        return Pango.FontDescription(self._desc)


class Color(object):

    def __init__(self, color, alpha=1.0):
        self._r, self._g, self._b = self._html_to_rgb(color)
        self._a = alpha

    def get_rgba(self):
        return (self._r, self._g, self._b, self._a)

    def get_int(self):
        return int(self._a * 255) + (int(self._b * 255) << 8) + \
            (int(self._g * 255) << 16) + (int(self._r * 255) << 24)

    def get_gdk_color(self):
        return Gdk.Color(int(self._r * 65535), int(self._g * 65535),
                         int(self._b * 65535))

    def get_html(self):
        return '#%02x%02x%02x' % (self._r * 255, self._g * 255, self._b * 255)

    def _html_to_rgb(self, html_color):
        """ #RRGGBB -> (r, g, b) tuple (in float format) """

        html_color = html_color.strip()
        if html_color[0] == '#':
            html_color = html_color[1:]
        if len(html_color) != 6:
            raise ValueError('input #%s is not in #RRGGBB format' % html_color)

        r, g, b = html_color[:2], html_color[2:4], html_color[4:]
        r, g, b = [int(n, 16) for n in (r, g, b)]
        r, g, b = (r / 255.0, g / 255.0, b / 255.0)

        return (r, g, b)

    def get_svg(self):
        if self._a == 0.0:
            return 'none'
        else:
            return self.get_html()


def zoom(units):
    return int(ZOOM_FACTOR * units)


ZOOM_FACTOR = _compute_zoom_factor()

DEFAULT_SPACING = zoom(15)
DEFAULT_PADDING = zoom(6)
GRID_CELL_SIZE = zoom(75)
LINE_WIDTH = zoom(2)

STANDARD_ICON_SIZE = zoom(55)
SMALL_ICON_SIZE = zoom(55 * 0.5)
MEDIUM_ICON_SIZE = zoom(55 * 1.5)
LARGE_ICON_SIZE = zoom(55 * 2.0)
XLARGE_ICON_SIZE = zoom(55 * 2.75)

settings = Gio.Settings('org.sugarlabs.font')
FONT_SIZE = settings.get_double('default-size')
FONT_FACE = settings.get_string('default-face')

FONT_NORMAL = Font('%s %f' % (FONT_FACE, FONT_SIZE))
FONT_BOLD = Font('%s bold %f' % (FONT_FACE, FONT_SIZE))
FONT_NORMAL_H = zoom(24)
FONT_BOLD_H = zoom(24)

TOOLBOX_SEPARATOR_HEIGHT = zoom(9)
TOOLBOX_HORIZONTAL_PADDING = zoom(75)
TOOLBOX_TAB_VBORDER = int((zoom(36) - FONT_NORMAL_H - FOCUS_LINE_WIDTH) / 2)
TOOLBOX_TAB_HBORDER = zoom(15) - FOCUS_LINE_WIDTH - _TAB_CURVATURE
TOOLBOX_TAB_LABEL_WIDTH = zoom(150 - 15 * 2)

COLOR_BLACK = Color('#000000')
COLOR_WHITE = Color('#FFFFFF')
COLOR_TRANSPARENT = Color('#FFFFFF', alpha=0.0)
COLOR_PANEL_GREY = Color('#C0C0C0')
COLOR_SELECTION_GREY = Color('#A6A6A6')
COLOR_TOOLBAR_GREY = Color('#282828')
COLOR_BUTTON_GREY = Color('#808080')
COLOR_INACTIVE_FILL = Color('#9D9FA1')
COLOR_INACTIVE_STROKE = Color('#757575')
COLOR_TEXT_FIELD_GREY = Color('#E5E5E5')
COLOR_HIGHLIGHT = Color('#E7E7E7')

PALETTE_CURSOR_DISTANCE = zoom(10)

TOOLBAR_ARROW_SIZE = zoom(24)

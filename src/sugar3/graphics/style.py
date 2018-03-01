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

'''
The style module defines constants for spacing and sizing, as well as
classes for  Colors and Fonts. Text rendering is handled by Pango and
colors are inputted by their HTML code (e.g. #FFFFFFFF)

All the constants are expressed in pixels. They are defined for the XO
screen and are usually adapted to different resolution by applying a
zoom factor.
'''

import os
import logging

from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import Gio


FOCUS_LINE_WIDTH = 2
_TAB_CURVATURE = 1
ELLIPSIZE_MODE_DEFAULT = Pango.EllipsizeMode.END


def _compute_zoom_factor():
    '''
    Calculates zoom factor based on size of screen.
    Returns double representing fraction of maximum possible screen size
    '''
    try:
        scaling = int(os.environ.get('SUGAR_SCALING', '100'))
        return scaling / 100.0
    except ValueError:
        logging.error('Invalid SUGAR_SCALING.')

    return 1.0


class Font(object):
    '''
    A font defines the style of how the text should be rendered.

    Args:
        desc (str): a description of the Font object
    '''

    def __init__(self, desc):
        self._desc = desc

    def __str__(self):
        '''
        Returns description of font
        '''
        return self._desc

    def get_pango_desc(self):
        '''
        Returns Pango description of font
        '''
        return Pango.FontDescription(self._desc)


class Color(object):
    '''
    A Color object defines a specific color.

    Args:
        color (str): String in the form #FFFFFF representing the color

        alpha (double):  transparency of color
    '''

    def __init__(self, color, alpha=1.0):
        self._r, self._g, self._b = self._html_to_rgb(color)
        self._a = alpha

    def get_rgba(self):
        '''
        Returns 4-tuple of red, green, blue, and alpha levels in range 0-1
        '''
        return (self._r, self._g, self._b, self._a)

    def get_int(self):
        '''
        Returns color encoded as an int, in the form rgba
        '''
        return int(self._a * 255) + (int(self._b * 255) << 8) + \
            (int(self._g * 255) << 16) + (int(self._r * 255) << 24)

    def get_gdk_color(self):
        '''
        Returns GDK standard color
        '''
        return Gdk.Color(int(self._r * 65535), int(self._g * 65535),
                         int(self._b * 65535))

    def get_html(self):
        '''
        Returns string in the standard html Color format (#FFFFFF)
        '''
        return '#%02x%02x%02x' % (
            int(self._r * 255), int(self._g * 255), int(self._b * 255))

    def _html_to_rgb(self, html_color):
        '''
        Converts and returns (r, g, b) tuple in float format from
        standard HTML format (#FFFFFF).  Colors will be in range 0-1

        Args:
            html_color (string): html string in the format #FFFFFF
        '''

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
        '''
        Returns HTML formatted color, unless the color is completely
        transparent, in which case returns "none"
        '''

        if self._a == 0.0:
            return 'none'
        else:
            return self.get_html()


def zoom(units):
    '''
    Returns size of units pixels at current zoom level

    Args:
        units (int): size of item at full size
    '''
    return int(ZOOM_FACTOR * units)


ZOOM_FACTOR = _compute_zoom_factor()  #: scale factor, as float (eg. 0.72, 1.0)

DEFAULT_SPACING = zoom(15)  #: Spacing is placed in-between elements
DEFAULT_PADDING = zoom(6)  #: Padding is placed around an element

#: allow elements to tile neatly within boundaries of a grid
#: http://wiki.sugarlabs.org/go/Human_Interface_Guidelines#The_Grid_System
GRID_CELL_SIZE = zoom(75)

LINE_WIDTH = zoom(2)  #: Thickness of a separator line

#: icon that fits within a grid cell
STANDARD_ICON_SIZE = zoom(55)
#: small icon, used in palette menu items
SMALL_ICON_SIZE = zoom(33)
#: larger than standard
MEDIUM_ICON_SIZE = zoom(55 * 1.5)
#: larger than medium, used in journal empty view
LARGE_ICON_SIZE = zoom(55 * 2.0)
#: larger than large, used in activity pulsing launcher icon
XLARGE_ICON_SIZE = zoom(55 * 2.75)

if 'org.sugarlabs.font' in Gio.Settings.list_schemas():
    settings = Gio.Settings('org.sugarlabs.font')
    #: User's preferred font size
    FONT_SIZE = settings.get_double('default-size')
    #: User's preferred font face
    FONT_FACE = settings.get_string('default-face')
else:
    #: User's preferred font size
    FONT_SIZE = 10
    #: User's preferred font face
    FONT_FACE = 'Sans Serif'

#: Normal font
FONT_NORMAL = Font('%s %f' % (FONT_FACE, FONT_SIZE))
#: Bold font
FONT_BOLD = Font('%s bold %f' % (FONT_FACE, FONT_SIZE))
#: Height in pixels of normal font
FONT_NORMAL_H = zoom(24)
#: Height in pixels of bold font
FONT_BOLD_H = zoom(24)

# old style toolbox design
TOOLBOX_SEPARATOR_HEIGHT = zoom(9)
TOOLBOX_HORIZONTAL_PADDING = zoom(75)
TOOLBOX_TAB_VBORDER = int((zoom(36) - FONT_NORMAL_H - FOCUS_LINE_WIDTH) / 2)
TOOLBOX_TAB_HBORDER = zoom(15) - FOCUS_LINE_WIDTH - _TAB_CURVATURE
TOOLBOX_TAB_LABEL_WIDTH = zoom(150 - 15 * 2)

COLOR_BLACK = Color('#000000')  #: Black
COLOR_WHITE = Color('#FFFFFF')  #: White
#: Fully transparent color
COLOR_TRANSPARENT = Color('#FFFFFF', alpha=0.0)
#: Default background color of a window
COLOR_PANEL_GREY = Color('#C0C0C0')
#: Background color of selected entry
COLOR_SELECTION_GREY = Color('#A6A6A6')
#: Color of toolbars
COLOR_TOOLBAR_GREY = Color('#282828')
#: Color of buttons
COLOR_BUTTON_GREY = Color('#808080')
#: Fill colour of an inactive button
COLOR_INACTIVE_FILL = Color('#9D9FA1')
#: Stroke colour of an inactive button
COLOR_INACTIVE_STROKE = Color('#757575')
#: Background color of entry
COLOR_TEXT_FIELD_GREY = Color('#E5E5E5')
#: Color of highlighted text
COLOR_HIGHLIGHT = Color('#E7E7E7')

#: Cursor invoked palettes will be placed this far from the cursor
PALETTE_CURSOR_DISTANCE = zoom(10)

#: Size of arrow displayed under toolbar buttons to represent their status
TOOLBAR_ARROW_SIZE = zoom(24)

#: Max width of text in a palette menu, in chars
MENU_WIDTH_CHARS = 60

# Copyright (C) 2013, One Laptop Per Child
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
A progress icon is a progress indicator in the form of an icon.
'''

from gi.repository import Gtk
from sugar3.graphics.icon import get_surface
from sugar3.graphics import style


class ProgressIcon(Gtk.DrawingArea):
    '''
    Display the progress filling the icon.
    This class is compatible with the sugar3.graphics.icon.Icon class.
    Call update(progress) with the new progress to update the icon.
    The direction defaults to 'vertical', in which case the icon is
    filled from bottom to top.  If direction is set to 'horizontal',
    it will be filled from right to left or from left to right,
    depending on the system's language RTL setting.
    Args:
      pixel_size (integer): sets the icon size
         [e.g. pixel_size=style.LARGE_ICON_SIZE]
      icon_name (string): Name of icon
         [e.g. icon_name='test_icon']
      stroke_color (string): Stroke color means border color.
      fill_color (string): The main (inside) color of progressicon
         [e.g. fill_color=style.COLOR_BLUE.get_svg()
      fill_start (float): fraction of the icon dimension where the
         fill area begins (0.0 = top or left edge).  Default is 0.0.
      fill_end (float): fraction of the icon dimension where the
         fill area ends (1.0 = bottom or right edge).  Default is 1.0.
         For icons whose fill region does not span the full icon, set
         fill_start and fill_end to the bounds of the fill area so
         that progress steps are distributed over that region instead
         of the entire surface.
    '''

    def __init__(self, icon_name, pixel_size, stroke_color, fill_color,
                 direction='vertical', fill_start=0.0, fill_end=1.0):
        Gtk.DrawingArea.__init__(self)

        self._icon_name = icon_name
        self._direction = direction
        self._progress = 0
        self._fill_start = fill_start
        self._fill_end = fill_end

        self._stroke = get_surface(
            icon_name=icon_name, width=pixel_size, height=pixel_size,
            stroke_color=stroke_color,
            fill_color=style.COLOR_TRANSPARENT.get_svg())

        self._fill = get_surface(
            icon_name=icon_name, width=pixel_size, height=pixel_size,
            stroke_color=style.COLOR_TRANSPARENT.get_svg(),
            fill_color=fill_color)

        self.connect("draw", self.__draw_cb)

    def __draw_cb(self, widget, cr):
        allocation = widget.get_allocation()

        # Center the graphic in the allocated space.
        margin_x = (allocation.width - self._stroke.get_width()) / 2
        margin_y = (allocation.height - self._stroke.get_height()) / 2
        cr.translate(margin_x, margin_y)

        # Paint the fill, clipping it by the progress.
        total_width = self._stroke.get_width()
        total_height = self._stroke.get_height()

        if self._direction == 'vertical':  # vertical direction, bottom to top
            fill_region = (self._fill_end - self._fill_start) * total_height
            # y_ is the bottom of the clip region (fill_end from the top).
            y_ = self._fill_end * total_height
            x_ = 0
            width = total_width
            height = fill_region * self._progress * -1
        else:
            fill_region = (self._fill_end - self._fill_start) * total_width
            rtl_direction = \
                Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL
            y_ = 0
            height = total_height
            if rtl_direction:  # horizontal direction, right to left
                x_ = self._fill_end * total_width
                width = fill_region * self._progress * -1
            else:  # horizontal direction, left to right
                x_ = self._fill_start * total_width
                width = fill_region * self._progress

        cr.rectangle(x_, y_, width, height)
        cr.clip()
        cr.set_source_surface(self._fill, 0, 0)
        cr.paint()

        # Paint the stroke over the fill.
        cr.reset_clip()
        cr.set_source_surface(self._stroke, 0, 0)
        cr.paint()

    def do_get_preferred_width(self):
        '''
        Calculate the minimum and natural width of the progressicon.
        '''
        width = self._stroke.get_width()
        return (width, width)

    def do_get_preferred_height(self):
        '''
        Calculate the minimum and natural height of the progressicon.
        '''
        height = self._stroke.get_height()
        return (height, height)

    def update(self, progress):
        '''
        Updates progressicon with progress's value.
        Example: update(0.9)
        '''
        self._progress = progress
        self.queue_draw()

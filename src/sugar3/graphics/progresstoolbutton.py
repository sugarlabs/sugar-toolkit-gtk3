#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016  Utkarsh Tiwari
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Contact information:
# Utkarsh Tiwari    iamutkarshtiwari@gmail.com

"""
BETA
"""

import logging

from gi.repository import Gtk
from gi.repository import GObject

from sugar3.graphics import style
from sugar3.graphics import toolbutton
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.icon import Icon
from sugar3.graphics.icon import get_surface
from sugar3.graphics.palette import Palette, ToolInvoker


class ProgressToolButton(ToolButton):
    """
    This class provides a simple wrapper based on the :class:`ToolButton`
    Displays the progress filling the ToolButton icon.

    Call update(progress) with the new progress to update the ToolButton icon.

    The direction defaults to 'vertical', in which case the icon is
    filled from bottom to top.  If direction is set to 'horizontal',
    it will be filled from right to left or from left to right,
    depending on the system's language RTL setting.
    """

    __gtype_name__ = 'SugarProgressToolButton'

    def __init__(self, icon_name=None, pixel_size=None,
                direction=Gtk.Orientation.VERTICAL, **kwargs):
        self._accelerator = None
        self._tooltip = None
        self._palette_invoker = ToolInvoker()
        self._progress = 0.0
        self._icon_name = icon_name
        self._pixel_size = pixel_size
        self._direction = direction

        GObject.GObject.__init__(self, **kwargs)

        self._hide_tooltip_on_click = True
        self._palette_invoker.attach_tool(self)

        self._stroke = get_surface(
            icon_name=self._icon_name, width=self._pixel_size, height=self._pixel_size,
            stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
            fill_color=style.COLOR_TRANSPARENT.get_svg())

        self._fill = get_surface(
            icon_name=self._icon_name, width=self._pixel_size, height=self._pixel_size,
            stroke_color=style.COLOR_TRANSPARENT.get_svg(),
            fill_color=style.COLOR_WHITE.get_svg())

    def do_draw(self, cr):
        if self.palette and self.palette.is_up():
            allocation = self.get_allocation()
            # draw a black background, has been done by the engine before
            cr.set_source_rgb(0, 0, 0)
            cr.rectangle(0, 0, allocation.width, allocation.height)
            cr.paint()

        if self.palette and self.palette.is_up():
            invoker = self.palette.props.invoker
            invoker.draw_rectangle(cr, self.palette)

        # Changes the outline color of the progressicon on activation
        if self._progress > 0:
            self._stroke = get_surface(
                icon_name=self._icon_name, width=self._pixel_size, height=self._pixel_size,
                stroke_color=style.COLOR_WHITE.get_svg(),
                fill_color=style.COLOR_TRANSPARENT.get_svg())
        else:
            self._stroke = get_surface(
                icon_name=self._icon_name, width=self._pixel_size, height=self._pixel_size,
                stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
                fill_color=style.COLOR_TRANSPARENT.get_svg())

        allocation = self.get_allocation()

        # Center the graphic in the allocated space.
        margin_x = (allocation.width - self._stroke.get_width()) / 2
        margin_y = (allocation.height - self._stroke.get_height()) / 2
        cr.translate(margin_x, margin_y)

        # Paint the fill, clipping it by the progress.
        x_, y_ = 0, 0
        width, height = self._stroke.get_width(), self._stroke.get_height()
        if self._direction == 'vertical':  # vertical direction, bottom to top
            y_ = self._stroke.get_height()
            height *= self._progress * -1
        else:
            rtl_direction = \
                Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL
            if rtl_direction:  # horizontal direction, right to left
                x_ = self._stroke.get_width()
                width *= self._progress * -1
            else:  # horizontal direction, left to right
                width *= self._progress

        cr.rectangle(x_, y_, width, height)
        cr.clip()
        cr.set_source_surface(self._fill, 0, 0)
        cr.paint()

        # Paint the stroke over the fill.
        cr.reset_clip()
        cr.set_source_surface(self._stroke, 0, 0)
        cr.paint()

        return False

    def update(self, progress):
        # Updates the progress
        self._progress = progress
        self.queue_draw()

# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2007-2008, One Laptop Per Child
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

from gi.repository import Gtk
from gi.repository import GObject

from sugar3.graphics.icon import Icon
from sugar3.graphics.palette import Palette, ToolInvoker
from sugar3.graphics import toolbutton


class RadioToolButton(Gtk.RadioToolButton):
    """An implementation of a "push" button."""

    __gtype_name__ = 'SugarRadioToolButton'

    def __init__(self, icon_name=None, **kwargs):
        self._accelerator = None
        self._tooltip = None
        self._xo_color = None
        self._palette_invoker = ToolInvoker()

        GObject.GObject.__init__(self, **kwargs)

        self._palette_invoker.attach_tool(self)
        self._hide_tooltip_on_click = True

        if icon_name:
            self.set_icon_name(icon_name)

        self.connect('destroy', self.__destroy_cb)

    def __destroy_cb(self, icon):
        if self._palette_invoker is not None:
            self._palette_invoker.detach()

    def set_tooltip(self, tooltip):
        if self.palette is None or self._tooltip is None:
            self.palette = Palette(tooltip)
        elif self.palette is not None:
            self.palette.set_primary_text(tooltip)

        self._tooltip = tooltip

        # Set label, shows up when toolbar overflows
        Gtk.RadioToolButton.set_label(self, tooltip)

    def get_tooltip(self):
        return self._tooltip

    tooltip = GObject.property(type=str, setter=set_tooltip,
        getter=get_tooltip)

    def set_accelerator(self, accelerator):
        self._accelerator = accelerator
        toolbutton.setup_accelerator(self)

    def get_accelerator(self):
        return self._accelerator

    accelerator = GObject.property(type=str, setter=set_accelerator,
            getter=get_accelerator)

    def set_icon_name(self, icon_name):
        icon = Icon(icon_name=icon_name,
                    xo_color=self._xo_color)
        self.set_icon_widget(icon)
        icon.show()

    def get_icon_name(self):
        if self.props.icon_widget is not None:
            return self.props.icon_widget.props.icon_name
        else:
            return None

    icon_name = GObject.property(type=str, setter=set_icon_name,
                                 getter=get_icon_name)

    def set_xo_color(self, xo_color):
        if self._xo_color != xo_color:
            self._xo_color = xo_color
            if self.props.icon_widget is not None:
                self.props.icon_widget.props.xo_color = xo_color

    def get_xo_color(self):
        return self._xo_color

    xo_color = GObject.property(type=object, setter=set_xo_color,
                                getter=get_xo_color)

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

    def do_draw(self, cr):
        child = self.get_child()
        allocation = self.get_allocation()

        if self.palette and self.palette.is_up():
            invoker = self.palette.props.invoker
            invoker.draw_rectangle(cr, self.palette)

            allocation = self.get_allocation()
            # draw a black background, has been done by the engine before
            cr.set_source_rgb(0, 0, 0)
            cr.rectangle(0, 0, allocation.width, allocation.height)
            cr.paint()

        Gtk.RadioToolButton.do_draw(self, cr)

    def get_hide_tooltip_on_click(self):
        return self._hide_tooltip_on_click

    def set_hide_tooltip_on_click(self, hide_tooltip_on_click):
        if self._hide_tooltip_on_click != hide_tooltip_on_click:
            self._hide_tooltip_on_click = hide_tooltip_on_click

    hide_tooltip_on_click = GObject.property(
        type=bool, default=True, getter=get_hide_tooltip_on_click,
        setter=set_hide_tooltip_on_click)

    def do_clicked(self):
        if self._hide_tooltip_on_click and self.palette:
            self.palette.popdown(True)

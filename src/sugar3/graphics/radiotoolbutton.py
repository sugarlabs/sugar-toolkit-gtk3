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

import gtk
import gobject

from sugar.graphics.icon import Icon
from sugar.graphics.palette import Palette, ToolInvoker
from sugar.graphics import toolbutton


class RadioToolButton(gtk.RadioToolButton):
    """
    An implementation of a "push" button.

    """

    __gtype_name__ = 'SugarRadioToolButton'

    def __init__(self, **kwargs):
        self._accelerator = None
        self._tooltip = None
        self._xo_color = None
        self._palette_invoker = ToolInvoker()

        gobject.GObject.__init__(self, **kwargs)

        self._palette_invoker.attach_tool(self)

        self.connect('destroy', self.__destroy_cb)

    def __destroy_cb(self, icon):
        if self._palette_invoker is not None:
            self._palette_invoker.detach()

    def set_tooltip(self, tooltip):
        """
        Set a simple palette with just a single label.

        Parameters
        ----------
        tooltip:

        Returns
        -------
        None

        """
        if self.palette is None or self._tooltip is None:
            self.palette = Palette(tooltip)
        elif self.palette is not None:
            self.palette.set_primary_text(tooltip)

        self._tooltip = tooltip

        # Set label, shows up when toolbar overflows
        gtk.RadioToolButton.set_label(self, tooltip)

    def get_tooltip(self):
        return self._tooltip

    tooltip = gobject.property(type=str, setter=set_tooltip,
        getter=get_tooltip)

    def set_accelerator(self, accelerator):
        """
        Sets the accelerator.

        Parameters
        ----------
        accelerator:

        Returns
        -------
        None

        """
        self._accelerator = accelerator
        toolbutton.setup_accelerator(self)

    def get_accelerator(self):
        """
        Returns the accelerator for the button.

        Parameters
        ----------
        None

        Returns
        ------
        accelerator:

        """
        return self._accelerator

    accelerator = gobject.property(type=str, setter=set_accelerator,
            getter=get_accelerator)

    def set_named_icon(self, named_icon):
        icon = Icon(icon_name=named_icon,
                    xo_color=self._xo_color,
                    icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR)
        self.set_icon_widget(icon)
        icon.show()

    def get_named_icon(self):
        if self.props.icon_widget is not None:
            return self.props.icon_widget.props.icon_name
        else:
            return None

    named_icon = gobject.property(type=str, setter=set_named_icon,
                                  getter=get_named_icon)

    def set_xo_color(self, xo_color):
        if self._xo_color != xo_color:
            self._xo_color = xo_color
            if self.props.icon_widget is not None:
                self.props.icon_widget.props.xo_color = xo_color

    def get_xo_color(self):
        return self._xo_color

    xo_color = gobject.property(type=object, setter=set_xo_color,
                                getter=get_xo_color)

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

    def do_expose_event(self, event):
        child = self.get_child()
        allocation = self.get_allocation()

        if self.palette and self.palette.is_up():
            invoker = self.palette.props.invoker
            invoker.draw_rectangle(event, self.palette)
        elif child.state == gtk.STATE_PRELIGHT:
            child.style.paint_box(event.window, gtk.STATE_PRELIGHT,
                                  gtk.SHADOW_NONE, event.area,
                                  child, 'toolbutton-prelight',
                                  allocation.x, allocation.y,
                                  allocation.width, allocation.height)

        gtk.RadioToolButton.do_expose_event(self, event)

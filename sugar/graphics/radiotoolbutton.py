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

import gtk
import gobject

from sugar.graphics.icon import Icon
from sugar.graphics.palette import Palette, ToolInvoker
from sugar.graphics import toolbutton

class RadioToolButton(gtk.RadioToolButton):
    __gtype_name__ = "SugarRadioToolButton"

    def __init__(self, named_icon=None, group=None, xo_color=None, **kwargs):
        self._accelerator = None
        self._tooltip = None
        self._palette = None
        self._xo_color = xo_color

        gobject.GObject.__init__(self, **kwargs)

        if named_icon:
            self.set_named_icon(named_icon)
        if group:
            self.props.group = group

    def set_tooltip(self, tooltip):
        """ Set a simple palette with just a single label.
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

    tooltip = gobject.property(type=str, setter=set_tooltip, getter=get_tooltip)

    def set_accelerator(self, accelerator):
        self._accelerator = accelerator
        toolbutton.setup_accelerator(self)

    def get_accelerator(self):
        return self._accelerator

    accelerator = gobject.property(type=str, setter=set_accelerator,
            getter=get_accelerator)

    def set_named_icon(self, named_icon):
        icon = Icon(icon_name=named_icon,
                    xo_color=self._xo_color,
                    icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR)
        self.set_icon_widget(icon)
        icon.show()

    def get_palette(self):
        return self._palette
    
    def set_palette(self, palette):
        if self._palette is not None:        
            self._palette.props.invoker = None
        self._palette = palette
        self._palette.props.invoker = ToolInvoker(self)

    palette = gobject.property(
            type=object, setter=set_palette, getter=get_palette)

    def do_expose_event(self, event):
        child = self.get_child()
        allocation = self.get_allocation()

        if self._palette and self._palette.is_up():
            invoker = self._palette.props.invoker
            invoker.draw_rectangle(event, self._palette)
        elif child.state == gtk.STATE_PRELIGHT:
            child.style.paint_box(event.window, gtk.STATE_PRELIGHT,
                                  gtk.SHADOW_NONE, event.area,
                                  child, "toolbutton-prelight",
                                  allocation.x, allocation.y,
                                  allocation.width, allocation.height)

        gtk.RadioToolButton.do_expose_event(self, event)


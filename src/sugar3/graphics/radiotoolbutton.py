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

'''
Provides a RadioToolButton class, similar to a "push" button.
A group of RadioToolButtons can be set, so that only one can be
selected at a time. When a button is clicked, it depresses and
is shaded darker.

It is also possible to set a tooltip to be dispalyed when the
user scrolls over it with their cursor as well as an accelerator
keyboard shortcut.

Example:
    .. literalinclude:: ../examples/radiotoolbutton.py
'''

from gi.repository import Gtk
from gi.repository import GObject

from sugar3.graphics.icon import Icon
from sugar3.graphics.palette import Palette, ToolInvoker
from sugar3.graphics import toolbutton


class RadioToolButton(Gtk.RadioToolButton):
    '''
    The RadioToolButton class manages a Gtk.RadioToolButton styled for
    Sugar.

    Args:
        icon_name (string): name of icon to be used.

    Keyword Args:

        accelerator (string): keyboard shortcut to be used to
            activate this button.

        tooltip (string): tooltip to be displayed when user hovers
            over button.

        xo_color (sugar3.graphics.xocolor.XoColor): XoColor of button.

        hide_tooltip_on_click (bool): Whether or not the tooltip
            is hidden when user clicks on button.
    '''

    __gtype_name__ = 'SugarRadioToolButton'

    def __init__(self, icon_name=None, **kwargs):
        self._accelerator = None
        self._tooltip = None
        self._xo_color = None
        self._hide_tooltip_on_click = True

        self._palette_invoker = ToolInvoker()

        GObject.GObject.__init__(self, **kwargs)

        self._palette_invoker.attach_tool(self)

        if icon_name:
            self.set_icon_name(icon_name)

        # HACK: stop Gtk from adding a label and expanding the size of
        # the button. This happen when set_icon_widget is called
        # if label_widget is None
        self.props.label_widget = Gtk.Box()

        self.connect('destroy', self.__destroy_cb)

    def __destroy_cb(self, icon):
        if self._palette_invoker is not None:
            self._palette_invoker.detach()

    def set_tooltip(self, tooltip):
        '''
        Set the tooltip.

        Args:
            tooltip (string): tooltip to be set.
        '''
        if self.palette is None or self._tooltip is None:
            self.palette = Palette(tooltip)
        elif self.palette is not None:
            self.palette.set_primary_text(tooltip)

        self._tooltip = tooltip

        # Set label, shows up when toolbar overflows
        Gtk.RadioToolButton.set_label(self, tooltip)

    def get_tooltip(self):
        '''
        Return the tooltip.
        '''
        return self._tooltip

    tooltip = GObject.Property(type=str, setter=set_tooltip,
                               getter=get_tooltip)

    def set_accelerator(self, accelerator):
        '''
        Set keyboard shortcut that activates this button.

        Args:
            accelerator (string): accelerator to be set. Should be in
            form <modifier>Letter.
        '''
        self._accelerator = accelerator
        toolbutton.setup_accelerator(self)

    def get_accelerator(self):
        '''
        Return accelerator string.
        '''
        return self._accelerator

    accelerator = GObject.Property(type=str, setter=set_accelerator,
                                   getter=get_accelerator)

    def set_icon_name(self, icon_name):
        '''
        Set name of icon.

        Args:
            icon_name (string): name of icon
        '''
        icon = Icon(icon_name=icon_name,
                    xo_color=self._xo_color)
        self.set_icon_widget(icon)
        icon.show()

    def get_icon_name(self):
        '''
        Return icon name, or None if there is no icon name.
        '''
        if self.props.icon_widget is not None:
            return self.props.icon_widget.props.icon_name
        else:
            return None

    icon_name = GObject.Property(type=str, setter=set_icon_name,
                                 getter=get_icon_name)

    def set_xo_color(self, xo_color):
        '''
        Set XoColor of button icon.

        Args:
            xo_color (sugar3.graphics.xocolor.XoColor): xocolor to be set.
        '''
        if self._xo_color != xo_color:
            self._xo_color = xo_color
            if self.props.icon_widget is not None:
                self.props.icon_widget.props.xo_color = xo_color

    def get_xo_color(self):
        '''
        Return xocolor.
        '''
        return self._xo_color

    xo_color = GObject.Property(type=object, setter=set_xo_color,
                                getter=get_xo_color)

    def create_palette(self):
        return None

    def get_palette(self):
        return self._palette_invoker.palette

    def set_palette(self, palette):
        self._palette_invoker.palette = palette

    palette = GObject.Property(
        type=object, setter=set_palette, getter=get_palette)

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = GObject.Property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker)

    def do_draw(self, cr):
        '''
        Implementation method for drawing the button.
        '''
        if self.palette and self.palette.is_up():
            allocation = self.get_allocation()
            # draw a black background, has been done by the engine before
            cr.set_source_rgb(0, 0, 0)
            cr.rectangle(0, 0, allocation.width, allocation.height)
            cr.paint()

        Gtk.RadioToolButton.do_draw(self, cr)

        if self.palette and self.palette.is_up():
            invoker = self.palette.props.invoker
            invoker.draw_rectangle(cr, self.palette)

        return False

    def get_hide_tooltip_on_click(self):
        '''
        Return True if the tooltip is hidden when a user
        clicks on the button, otherwise return False.
        '''
        return self._hide_tooltip_on_click

    def set_hide_tooltip_on_click(self, hide_tooltip_on_click):
        '''
        Set whether or not the tooltip is hidden when a user
        clicks on the button.

        Args:
            hide_tooltip_on_click (bool): True if the tooltip is
            hidden on click, and False otherwise.
        '''
        if self._hide_tooltip_on_click != hide_tooltip_on_click:
            self._hide_tooltip_on_click = hide_tooltip_on_click

    hide_tooltip_on_click = GObject.Property(
        type=bool, default=True, getter=get_hide_tooltip_on_click,
        setter=set_hide_tooltip_on_click)

    def do_clicked(self):
        '''
        Implementation method for hiding the tooltip when
        the button is clicked.
        '''
        if self._hide_tooltip_on_click and self.palette:
            self.palette.popdown(True)

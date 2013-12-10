# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2008, One Laptop Per Child
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

import logging

from gi.repository import Gtk
from gi.repository import GObject

from sugar3.graphics.icon import Icon
from sugar3.graphics.palette import Palette, ToolInvoker


def _add_accelerator(tool_button):
    if not tool_button.props.accelerator or not tool_button.get_toplevel() or \
            not tool_button.get_child():
        return

    # TODO: should we remove the accelerator from the prev top level?
    if not hasattr(tool_button.get_toplevel(), 'sugar_accel_group'):
        logging.warning('No Gtk.AccelGroup in the top level window.')
        return

    accel_group = tool_button.get_toplevel().sugar_accel_group
    keyval, mask = Gtk.accelerator_parse(tool_button.props.accelerator)
    # the accelerator needs to be set at the child, so the Gtk.AccelLabel
    # in the palette can pick it up.
    tool_button.get_child(
    ).add_accelerator('clicked', accel_group, keyval, mask,
                      Gtk.AccelFlags.LOCKED | Gtk.AccelFlags.VISIBLE)


def _hierarchy_changed_cb(tool_button, previous_toplevel):
    _add_accelerator(tool_button)


def setup_accelerator(tool_button):
    _add_accelerator(tool_button)
    tool_button.connect('hierarchy-changed', _hierarchy_changed_cb)


class ToolButton(Gtk.ToolButton):

    __gtype_name__ = 'SugarToolButton'

    def __init__(self, icon_name=None, **kwargs):
        self._accelerator = None
        self._tooltip = None
        self._palette_invoker = ToolInvoker()

        GObject.GObject.__init__(self, **kwargs)

        self._hide_tooltip_on_click = True
        self._palette_invoker.attach_tool(self)

        if icon_name:
            self.set_icon_name(icon_name)

        self.get_child().connect('can-activate-accel',
                                 self.__button_can_activate_accel_cb)

        self.connect('destroy', self.__destroy_cb)

    def __destroy_cb(self, icon):
        if self._palette_invoker is not None:
            self._palette_invoker.detach()

    def __button_can_activate_accel_cb(self, button, signal_id):
        # Accept activation via accelerators regardless of this widget's state
        return True

    def set_tooltip(self, tooltip):
        """ Set a simple palette with just a single label.
        """
        if self.palette is None or self._tooltip is None:
            self.palette = Palette(tooltip)
        elif self.palette is not None:
            self.palette.set_primary_text(tooltip)

        self._tooltip = tooltip

        # Set label, shows up when toolbar overflows
        Gtk.ToolButton.set_label(self, tooltip)

    def get_tooltip(self):
        return self._tooltip

    tooltip = GObject.property(type=str, setter=set_tooltip,
                               getter=get_tooltip)

    def get_hide_tooltip_on_click(self):
        return self._hide_tooltip_on_click

    def set_hide_tooltip_on_click(self, hide_tooltip_on_click):
        if self._hide_tooltip_on_click != hide_tooltip_on_click:
            self._hide_tooltip_on_click = hide_tooltip_on_click

    hide_tooltip_on_click = GObject.property(
        type=bool, default=True, getter=get_hide_tooltip_on_click,
        setter=set_hide_tooltip_on_click)

    def set_accelerator(self, accelerator):
        self._accelerator = accelerator
        setup_accelerator(self)

    def get_accelerator(self):
        return self._accelerator

    accelerator = GObject.property(type=str, setter=set_accelerator,
                                   getter=get_accelerator)

    def set_icon_name(self, icon_name):
        icon = Icon(icon_name=icon_name)
        self.set_icon_widget(icon)
        icon.show()

    def get_icon_name(self):
        if self.props.icon_widget is not None:
            return self.props.icon_widget.props.icon_name
        else:
            return None

    icon_name = GObject.property(type=str, setter=set_icon_name,
                                 getter=get_icon_name)

    def create_palette(self):
        return None

    def get_palette(self):
        return self._palette_invoker.palette

    def set_palette(self, palette):
        self._palette_invoker.palette = palette
        self.palette.set_parent_widget(self)

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
        if self.palette and self.palette.is_up():
            allocation = self.get_allocation()
            # draw a black background, has been done by the engine before
            cr.set_source_rgb(0, 0, 0)
            cr.rectangle(0, 0, allocation.width, allocation.height)
            cr.paint()

        Gtk.ToolButton.do_draw(self, cr)

        if self.palette and self.palette.is_up():
            invoker = self.palette.props.invoker
            invoker.draw_rectangle(cr, self.palette)

        return False

    def do_clicked(self):
        if self._hide_tooltip_on_click and self.palette:
            self.palette.popdown(True)

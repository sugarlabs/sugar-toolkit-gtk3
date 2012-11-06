# Copyright (C) 2009, Aleksey Lim
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

from gi.repository import Gtk

from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.palette import Palette


class RadioMenuButton(ToolButton):

    def __init__(self, **kwargs):
        ToolButton.__init__(self, **kwargs)
        self.selected_button = None

        self.palette_invoker.props.toggle_palette = True
        self.props.hide_tooltip_on_click = False

        if self.props.palette:
            self.__palette_cb(None, None)

        self.connect('notify::palette', self.__palette_cb)

    def __palette_cb(self, widget, pspec):
        if not isinstance(self.props.palette, RadioPalette):
            return
        self.props.palette.update_button()


class RadioToolsButton(RadioMenuButton):

    def __init__(self, **kwargs):
        RadioMenuButton.__init__(self, **kwargs)

    def do_clicked(self):
        if not self.selected_button:
            return
        self.selected_button.emit('clicked')


class RadioPalette(Palette):

    def __init__(self, **kwargs):
        Palette.__init__(self, **kwargs)

        self.button_box = Gtk.HBox()
        self.button_box.show()
        self.set_content(self.button_box)

    def append(self, button, label):
        children = self.button_box.get_children()

        if button.palette is not None:
            raise RuntimeError("Palette's button should not have sub-palettes")

        button.show()
        button.connect('clicked', self.__clicked_cb)
        self.button_box.pack_start(button, True, False, 0)
        button.palette_label = label

        if not children:
            self.__clicked_cb(button)

    def update_button(self):
        for i in self.button_box.get_children():
            self.__clicked_cb(i)

    def __clicked_cb(self, button):
        if not button.get_active():
            return

        self.set_primary_text(button.palette_label)
        self.popdown(immediate=True)

        if self.invoker is not None:
            parent = self.invoker.parent
        else:
            parent = None
        if not isinstance(parent, RadioMenuButton):
            return

        parent.props.label = button.palette_label
        parent.set_icon_name(button.props.icon_name)
        parent.selected_button = button

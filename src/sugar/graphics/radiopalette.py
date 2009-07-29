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

import gtk
import gobject
import logging
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_PYOBJECT

from sugar.graphics import style
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.palette import Palette

class RadioPaletteButton(ToolButton):
    def __init__(self, **kwargs):
        ToolButton.__init__(self, **kwargs)
        self.selected_button = None

        if self.props.palette:
            self.__palette_cb(None, None)

        self.connect('notify::palette', self.__palette_cb)

    def __palette_cb(self, widget, pspec):
        if not isinstance(self.props.palette, RadioPalette):
            return
        self.props.palette.update_button()

class RadioMenuButton(RadioPaletteButton):
    def __init__(self, **kwargs):
        RadioPaletteButton.__init__(self, **kwargs)

    def do_clicked(self):
        if not self.palette:
            return
        if self.palette.is_up() and \
                self.palette.palette_state == Palette.SECONDARY:
            self.palette.popdown(immediate=True)
        else:
            self.palette.popup(immediate=True, state=Palette.SECONDARY)

    def do_expose_event(self, event):
        ToolButton.do_expose_event(self, event)
        if not self.palette:
            return

        if self.palette.is_up():
            type = gtk.ARROW_DOWN
        else:
            type = gtk.ARROW_UP

        a = self.allocation
        self.get_style().paint_arrow(event.window,
                gtk.STATE_NORMAL, gtk.SHADOW_IN, event.area, self,
                None, type,  True,
                a.x + a.width/2 - style.TOOLBAR_ARROW_SIZE/2,
                a.y + a.height - style.TOOLBAR_ARROW_SIZE - \
                        style._FOCUS_LINE_WIDTH,
                style.TOOLBAR_ARROW_SIZE, style.TOOLBAR_ARROW_SIZE)

class RadioToolsButton(RadioPaletteButton):
    def __init__(self, **kwargs):
        RadioPaletteButton.__init__(self, **kwargs)

    def do_clicked(self):
        if not self.selected_button:
            return
        self.selected_button.emit('clicked')

class RadioPalette(Palette):
    def __init__(self, **kwargs):
        Palette.__init__(self, **kwargs)

        self.top = gtk.HBox()
        self.top.show()
        self.set_content(self.top)

    def append(self, button, label):
        children = self.top.get_children()

        # palette's button should not have sub-palettes
        button.palette = None

        button.show()
        button.connect('clicked', self.__clicked_cb)
        self.top.pack_start(button, fill=False)
        button.__palette_label = label

        if not children:
            self.__clicked_cb(button, True)

    def update_button(self):
        for i in self.top.get_children():
            self.__clicked_cb(i, True)

    def __clicked_cb(self, button, quiet=False):
        if not button.get_active():
            return

        self.set_primary_text(button.__palette_label)
        if not quiet:
            self.popdown(immediate=True)

        parent = self.invoker and self.invoker.parent
        if not isinstance(parent, RadioPaletteButton):
            return

        parent.set_icon(button.props.icon_name)
        parent.selected_button = button

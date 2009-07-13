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
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE

from sugar.graphics import style
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.palette import Palette
from sugar.graphics.radiotoolbutton import RadioToolButton

ARROW_SIZE = hasattr(style, 'TOOLBAR_ARROW_SIZE') and style.TOOLBAR_ARROW_SIZE \
        or 8

class RadioPaletteButton(ToolButton):
    def __init__(self, **kwargs):
        ToolButton.__init__(self, **kwargs)

        self._button_cb = None

        if self.props.palette:
            self.__palette_cb(None, None)

        self.connect('notify::palette', self.__palette_cb)

    def __palette_cb(self, widget, pspec):
        if not isinstance(self.props.palette, RadioPalette):
            return
        self.props.palette.update_button()

    def _set_current_button(self, button):
        self.set_icon(button.rp_icon_name)
        self._button_cb = button.rp_toggled_cb

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
                a.x + a.width/2 - ARROW_SIZE/2,
                a.y + a.height - ARROW_SIZE - style._FOCUS_LINE_WIDTH,
                ARROW_SIZE, ARROW_SIZE)

class RadioToolsButton(RadioPaletteButton):
    def __init__(self, **kwargs):
        RadioPaletteButton.__init__(self, **kwargs)

    def do_clicked(self):
        if not self._button_cb:
            return
        self._button_cb()

class RadioPalette(Palette):
    def __init__(self, **kwargs):
        Palette.__init__(self, **kwargs)

        self.top = gtk.HBox()
        self.top.show()
        self.set_content(self.top)

    def append(self, icon_name, tooltip=None, toggled_cb=None):
        children = self.top.get_children()
        button = RadioToolButton(icon_name=icon_name,
                group=children and children[0] or None)
        button.show()
        button.connect('toggled', self.__toggled_cb)
        self.top.pack_start(button, fill=False)

        button.rp_icon_name = icon_name
        button.rp_tooltip = tooltip
        button.rp_toggled_cb = toggled_cb

        if not children:
            self.__toggled_cb(button, True)

        return button

    def update_button(self):
        for i in self.top.get_children():
            self.__toggled_cb(i, True)

    def __toggled_cb(self, button, quiet=False):
        if not button.get_active():
            return

        self.set_primary_text(button.rp_tooltip)
        if not quiet:
            if button.rp_toggled_cb:
                button.rp_toggled_cb()
            self.popdown(immediate=True)

        if not self.invoker or \
                not isinstance(self.invoker.parent, RadioPaletteButton):
            return

        self.invoker.parent._set_current_button(button)

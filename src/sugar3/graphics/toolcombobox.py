# Copyright (C) 2007, Red Hat, Inc.
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

from sugar3.graphics.combobox import ComboBox
from sugar3.graphics import style


class ToolComboBox(Gtk.ToolItem):

    __gproperties__ = {
        'label-text': (str, None, None, None, GObject.ParamFlags.WRITABLE),
    }

    def __init__(self, combo=None, **kwargs):
        self.label = None
        self._label_text = ''

        GObject.GObject.__init__(self, **kwargs)

        self.set_border_width(style.DEFAULT_PADDING)

        hbox = Gtk.HBox(False, style.DEFAULT_SPACING)

        self.label = Gtk.Label(label=self._label_text)
        hbox.pack_start(self.label, False, False, 0)
        self.label.show()

        if combo:
            self.combo = combo
        else:
            self.combo = ComboBox()

        hbox.pack_start(self.combo, True, True, 0)
        self.combo.show()

        self.add(hbox)
        hbox.show()

    def do_set_property(self, pspec, value):
        if pspec.name == 'label-text':
            self._label_text = value
            if self.label:
                self.label.set_text(self._label_text)

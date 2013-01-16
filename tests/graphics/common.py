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

from gi.repository import Gtk
from gi.repository import GObject

from sugar3.graphics.toolbutton import ToolButton

import os


def set_theme():
    settings = Gtk.Settings.get_default()
    sugar_theme = 'sugar-72'
    if 'SUGAR_SCALING' in os.environ:
        if os.environ['SUGAR_SCALING'] == '100':
            sugar_theme = 'sugar-100'
    settings.set_property('gtk-theme-name', sugar_theme)
    settings.set_property('gtk-icon-theme-name', 'sugar')
set_theme()

class Test(Gtk.VBox):
    def __init__(self):
        GObject.GObject.__init__(self)


class TestPalette(Test):
    def __init__(self):
        Test.__init__(self)

        toolbar = Gtk.Toolbar()

        self._invoker = ToolButton('go-previous')
        toolbar.insert(self._invoker, -1)
        self._invoker.show()

        self.pack_start(toolbar, False)
        toolbar.show()

    def set_palette(self, palette):
        self._invoker.set_palette(palette)


class TestRunner(object):
    def run(self, test):
        window = Gtk.Window()
        window.connect('destroy', lambda w: Gtk.main_quit())
        window.add(test)
        test.show()

        window.show()


def main(test):
    runner = TestRunner()
    runner.run(test)

    Gtk.main()

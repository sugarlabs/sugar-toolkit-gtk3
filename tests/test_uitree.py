# Copyright (C) 2012, Daniel Narvaez
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import sys
import subprocess
import unittest

from sugar3.test import uitree


class TestUITree(unittest.TestCase):
    def test_tree(self):
        process = subprocess.Popen(["python3", __file__, "show_window1"])

        try:
            root = uitree.get_root()
            window = root.find_child(name="window1", role_name="frame")
            button = window.find_child(name="button1", role_name="push button")
        finally:
            process.terminate()

        self.assertIsNotNone(button)
   def test_find_menu_item(self):
        process = subprocess.Popen(["python3", __file__, "show_window2"])

        try:
            root = uitree.get_root()
            window = root.find_child(name="window2", role_name="frame")
            menu = window.find_child(name="menu1", role_name="menu")
            item = menu.find_child(name="item1", role_name="menu item")
        finally:
            process.terminate()

        self.assertIsNotNone(item)

    def test_find_checkbox(self):
        process = subprocess.Popen(["python3", __file__, "show_window3"])

        try:
            root = uitree.get_root()
            window = root.find_child(name="window3", role_name="frame")
            checkbox = window.find_child(name="checkbox1", role_name="check box")
        finally:
            process.terminate()

        self.assertIsNotNone(checkbox)

    def test_find_text_field(self):
        process = subprocess.Popen(["python3", __file__, "show_window4"])

        try:
            root = uitree.get_root()
            window = root.find_child(name="window4", role_name="frame")
            text_field = window.find_child(name="text1", role_name="text")
        finally:
            process.terminate()

        self.assertIsNotNone(text_field)



def show_window1():
    from gi.repository import Gtk

    window = Gtk.Window()
    window.set_title("window1")

    button = Gtk.Button(label="button1")
    window.add(button)
    button.show()

    window.show()

    Gtk.main()
def show_window2():
    from gi.repository import Gtk

    window = Gtk.Window()
    window.set_title("window2")

    menu_bar = Gtk.MenuBar()
    window.add(menu_bar)

    menu = Gtk.Menu()
    menu_item = Gtk.MenuItem(label="item1")
    menu_item.set_submenu(menu)
    menu_bar.add(menu_item)
    menu.show()

    window.show()

    Gtk.main()

def show_window3():
    from gi.repository import Gtk

    window = Gtk.Window()
    window.set_title("window3")

    checkbox = Gtk.CheckButton(label="checkbox1")
    window.add(checkbox)
    checkbox.show()

    window.show()

    Gtk.main()

def show_window4():
    from gi.repository import Gtk

    window = Gtk.Window()
    window.set_title("window4")

    text_field = Gtk.Entry()
    window.add(text_field)
    text_field.show()

    window.show()

    Gtk.main()


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUITree)
    unittest.TextTestRunner().run(suite)



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
        process = subprocess.Popen(["python", __file__, "show_window1"])

        try:
            root = uitree.get_root()
            window = root.find_child(name="window1", role_name="frame")
            button = window.find_child(name="button1", role_name="push button")
        finally:
            process.terminate()

        self.assertIsNotNone(button)


def show_window1():
    from gi.repository import Gtk

    window = Gtk.Window()
    window.set_title("window1")

    button = Gtk.Button(label="button1")
    window.add(button)
    button.show()

    window.show()

    Gtk.main()

if __name__ == '__main__':
    globals()[sys.argv[1]]()

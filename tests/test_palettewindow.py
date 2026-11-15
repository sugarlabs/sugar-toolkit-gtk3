# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from unittest.mock import patch

import gi

# Select the GTK 3 bindings before importing them or the toolkit.
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gtk  # noqa: E402

from sugar3.graphics.palettewindow import Invoker  # noqa: E402


class RectangleInvoker(Invoker):
    def get_rect(self):
        return self.rectangle


class TestInvokerScreenResize(unittest.TestCase):
    def setUp(self):
        self.width = patch.object(Gdk.Screen, 'width', return_value=1024)
        self.height = patch.object(Gdk.Screen, 'height', return_value=768)
        self.screen_width = self.width.start()
        self.screen_height = self.height.start()
        self.addCleanup(self.width.stop)
        self.addCleanup(self.height.stop)
        self.invoker = RectangleInvoker()
        self.invoker._cursor_x = self.invoker._cursor_y = 0
        self.invoker.rectangle = Gdk.Rectangle()
        self.invoker.rectangle.x = 1100
        self.invoker.rectangle.y = 40
        self.invoker.rectangle.width = 40
        self.invoker.rectangle.height = 40
        self.dimensions = Gtk.Requisition()
        self.dimensions.width = 180
        self.dimensions.height = 80

    def test_position_after_screen_expands(self):
        self.screen_width.return_value = 1280
        self.screen_height.return_value = 960
        position = self.invoker.get_position(self.dimensions)
        self.assertEqual((position.x, position.y), (1100, 80))

    def test_alignment_after_screen_expands(self):
        self.screen_width.return_value = 1280
        self.screen_height.return_value = 960
        position = self.invoker.get_position_for_alignment(
            self.invoker.BOTTOM[0], self.dimensions)
        self.assertIsNotNone(position)
        self.assertEqual((position.x, position.y), (1100, 80))

    def test_position_after_screen_shrinks(self):
        self.screen_width.return_value = 800
        self.screen_height.return_value = 600
        self.invoker.rectangle.x = 720
        position = self.invoker.get_position(self.dimensions)
        self.assertEqual((position.x, position.y), (580, 80))

    def test_height_change_repositions_palette(self):
        self.screen_height.return_value = 480
        self.invoker.rectangle.x = 100
        self.invoker.rectangle.y = 400
        position = self.invoker.get_position(self.dimensions)
        self.assertLessEqual(position.y + position.height, 480)


if __name__ == '__main__':
    unittest.main()

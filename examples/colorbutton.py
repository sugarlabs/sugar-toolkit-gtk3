from gi.repository import Gtk

from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.colorbutton import ColorToolButton


import common


test = common.Test()
test.show()

box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
test.pack_start(box, True, True, 0)
box.show()

toolbar_box = ToolbarBox()
box.pack_start(toolbar_box, False, False, 0)
toolbar_box.show()

separator = Gtk.SeparatorToolItem()
toolbar_box.toolbar.insert(separator, -1)
separator.show()


def color_changed_cb(button, pspec):
    print button.get_color()


color_button = ColorToolButton()
color_button.connect("notify::color", color_changed_cb)
toolbar_box.toolbar.insert(color_button, -1)
color_button.show()


if __name__ == '__main__':
    common.main(test)

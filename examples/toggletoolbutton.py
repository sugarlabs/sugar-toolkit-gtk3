from gi.repository import Gtk

from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toggletoolbutton import ToggleToolButton

import common


test = common.Test()
test.show()

box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
test.pack_start(box, True, True, 0)
box.show()

toolbar_box = ToolbarBox()
box.pack_start(toolbar_box, False, False, 0)
toolbar_box.show()

favorite_button = ToggleToolButton('emblem-favorite')
favorite_button.set_tooltip('Favorite')
toolbar_box.toolbar.insert(favorite_button, -1)
favorite_button.show()

favorite_button2 = ToggleToolButton('emblem-favorite')
favorite_button2.set_tooltip('Favorite')
toolbar_box.toolbar.insert(favorite_button2, -1)
favorite_button2.set_active(True)
favorite_button2.show()


if __name__ == '__main__':
    common.main(test)

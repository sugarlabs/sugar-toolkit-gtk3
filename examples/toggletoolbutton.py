from gi.repository import Gtk

from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toggletoolbutton import ToggleToolButton

import common


test = common.Test()
test.show()

vbox = Gtk.VBox()
test.pack_start(vbox, True, True, 0)
vbox.show()

toolbar_box = ToolbarBox()
vbox.pack_start(toolbar_box, False, False, 0)
toolbar_box.show()

separator = Gtk.SeparatorToolItem()
toolbar_box.toolbar.insert(separator, -1)
separator.show()

favorite_button = ToggleToolButton('emblem-favorite')
favorite_button.set_tooltip('Favorite')
toolbar_box.toolbar.insert(favorite_button, -1)
favorite_button.show()


if __name__ == '__main__':
    common.main(test)

from gi.repository import Gtk

from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.colorbutton import ColorToolButton
from sugar3.graphics.radiotoolbutton import RadioToolButton
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

radial_button = RadioToolButton(icon_name='view-radial')
toolbar_box.toolbar.insert(radial_button, -1)
radial_button.show()

list_button = RadioToolButton(icon_name='view-list')
list_button.props.group = radial_button
toolbar_box.toolbar.insert(list_button, -1)
list_button.show()

separator = Gtk.SeparatorToolItem()
toolbar_box.toolbar.insert(separator, -1)
separator.show()

color_button = ColorToolButton()
toolbar_box.toolbar.insert(color_button, -1)
color_button.show()

favorite_button = ToggleToolButton('emblem-favorite')
favorite_button.set_tooltip('Favorite')
toolbar_box.toolbar.insert(favorite_button, -1)
favorite_button.show()


if __name__ == '__main__':
    common.main(test)

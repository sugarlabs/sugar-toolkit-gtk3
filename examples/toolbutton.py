from gi.repository import Gtk

from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbutton import ToolButton

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

Tool_Button = ToolButton(icon_name='view-radial')
toolbar_box.toolbar.insert(Tool_Button, -1)
Tool_Button.show()

if __name__ == '__main__':
    common.main(test)

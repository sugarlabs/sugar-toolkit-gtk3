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

tool_button = ToolButton(icon_name='view-radial', tooltip='A toolbutton')
toolbar_box.toolbar.insert(tool_button, -1)
tool_button.show()

if __name__ == '__main__':
    common.main(test)

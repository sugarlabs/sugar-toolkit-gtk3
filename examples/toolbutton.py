from gi.repository import Gtk

from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbutton import ToolButton

import common


test = common.Test()

vbox = Gtk.VBox()
test.pack_start(vbox, True, True, 0)

toolbar_box = ToolbarBox()
vbox.pack_start(toolbar_box, False, False, 0)

separator = Gtk.SeparatorToolItem()
toolbar_box.toolbar.insert(separator, -1)


def __clicked_cb(button):
    n = int(button.get_tooltip())
    button.set_tooltip(str(n+1))
    print "tool button click count %d" % n

tool_button = ToolButton(icon_name='view-radial', tooltip='0')
tool_button.connect('clicked', __clicked_cb)
tool_button.set_hide_tooltip_on_click(False)
tool_button.set_accelerator('<Space>')
toolbar_box.toolbar.insert(tool_button, -1)

test.show_all()

if __name__ == '__main__':
    common.main(test)

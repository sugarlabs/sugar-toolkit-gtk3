#!/usr/bin/python
from gi.repository import Gtk

from sugar3.graphics.icon import Icon

import common
test = common.Test()
test.show()

box = Gtk.HBox()
test.pack_start(box, True, True, 0)
box.show()

# notebook without button

notebook = Gtk.Notebook()
box.pack_start(notebook, True, True, 0)
notebook.show()

for i in range(3):
    hbox = Gtk.HBox()
    notebook.append_page(hbox, Gtk.Label('Page %d' % (i + 1)))
    hbox.show()

# notebook with buttons 

notebook = Gtk.Notebook()
box.pack_start(notebook, True, True, 0)
notebook.show()

add_icon = Icon(icon_name='add')
button = Gtk.Button()
button.props.focus_on_click = False
button.add(add_icon)
add_icon.show()

notebook.set_action_widget(button, Gtk.PackType.END)
button.show()

for i in range(3):
    hbox = Gtk.HBox()
    notebook.append_page(hbox, Gtk.Label('Page %d' % (i + 1)))
    hbox.show()

if __name__ == '__main__':
    common.main(test)

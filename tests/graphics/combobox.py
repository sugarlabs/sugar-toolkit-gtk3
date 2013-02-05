from gi.repository import Gtk

import common


test = common.Test()
test.show()

# test Gtk.ComboBox:

store = Gtk.ListStore(int, str)
for i in range(100):
    description = "combo test entry %d" % i
    store.append([i, description])

combobox = Gtk.ComboBox(model=store)
cell = Gtk.CellRendererText()
combobox.pack_start(cell, True)
combobox.add_attribute(cell, 'text', 1)
test.pack_start(combobox, True, True, 0)
combobox.show()

if __name__ == '__main__':
    common.main(test)

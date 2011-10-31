from gi.repository import Gtk

from sugar3.graphics.combobox import ComboBox

def _destroy_cb(widget, data=None):
    Gtk.main_quit()

def __combo_changed_cb(widget, data=None):
    print 'combo-changed'

w = Gtk.Window()
w.connect("destroy", _destroy_cb)

box = Gtk.VBox()
w.add(box)

combo = ComboBox()
combo.append_item(0, 'one')
combo.append_item(1, 'two', 'go-next')
combo.append_item(2, 'three')
combo.set_active(1)
combo.connect('changed', __combo_changed_cb)
box.pack_start(combo, False, False, 0)

w.show_all()

Gtk.main()

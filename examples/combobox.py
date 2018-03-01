from gi.repository import Gtk

from sugar3.graphics.combobox import ComboBox
from common import set_theme
set_theme()


def __combo_changed_cb(combo):
    print('Combo changed to %r' % combo.get_value())


w = Gtk.Window()
w.connect("delete-event", Gtk.main_quit)

combo = ComboBox()
combo.append_item(True, 'one')
combo.append_item(2, 'two', 'go-next')
combo.append_item('3', 'three')
# This will make 'two' active (zero indexed)
combo.set_active(1)
combo.connect('changed', __combo_changed_cb)
w.add(combo)

w.show_all()
Gtk.main()

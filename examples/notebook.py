from gi.repository import Gtk

from sugar3.graphics.notebook import Notebook
from common import set_theme
set_theme()


w = Gtk.Window()
w.connect("delete-event", Gtk.main_quit)

box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
w.add(box)

nb = Notebook(can_close_tabs=True)
box.pack_start(nb, False, False, 0)

for i in range(5):
    bufferf = "Prepend Frame %d" % (i + 1)
    bufferl = "PPage %d" % (i + 1)

    frame = Gtk.Frame()
    frame.set_border_width(10)
    frame.set_size_request(100, 75)
    label = Gtk.Label(bufferf)
    frame.add(label)
    label.show()
    nb.add_page(bufferl, frame)
    frame.show()

w.show_all()

Gtk.main()

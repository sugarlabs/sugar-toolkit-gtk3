from gi.repository import Gtk

from sugar3.graphics.notebook import Notebook

def _destroy_cb(widget, data=None):
    Gtk.main_quit()

w = Gtk.Window()
w.connect("destroy", _destroy_cb)

box = Gtk.VBox()
w.add(box)

nb = Notebook(can_close_tabs=True)
box.pack_start(nb, False, False, 0)

for i in range(5):
    bufferf = "Prepend Frame %d" % (i+1)
    bufferl = "PPage %d" % (i+1)

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

from gi.repository import Gtk

"""
Since GTK+3 Gtk.CellRenderer doesn't have a destroy signal anymore.
We can do the cleanup in the python destructor method instead.

"""


class MyCellRenderer(Gtk.CellRenderer):

    def __init__(self):
        Gtk.CellRenderer.__init__(self)

    def __del__(self):
        print "cellrenderer destroy"

    def do_render(self, cairo_t, widget, background_area, cell_area, flags):
        pass


def window_destroy_cb(*kwargs):
    print "window destroy"
    Gtk.main_quit()


window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
window.connect("destroy", window_destroy_cb)
window.show()


def treeview_destroy_cb(*kwargs):
    print "treeview destroy"


treeview = Gtk.TreeView()
treeview.connect("destroy", treeview_destroy_cb)
window.add(treeview)
treeview.show()

col = Gtk.TreeViewColumn()
treeview.append_column(col)

cel = MyCellRenderer()
col.pack_start(cel, expand=True)

Gtk.main()

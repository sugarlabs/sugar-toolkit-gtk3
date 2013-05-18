"""

http://developer.gnome.org/gtk3/stable/GtkCellRendererProgress.html

"""

from gi.repository import Gtk

from sugar3.graphics import style

import common


test = common.Test()
test.show()

model = Gtk.ListStore(str, int, int)
for item in [('one', 72, -1),
             ('two', 50, -1),
             ('three', 35, -1),
             ('four', 0, 5)]:
    model.append(item)

treeview = Gtk.TreeView()
treeview.set_model(model)
treeview.set_headers_visible(False)
test.pack_start(treeview, True, True, 0)
treeview.show()

col = Gtk.TreeViewColumn()
treeview.append_column(col)

cell_text = Gtk.CellRendererText()
cell_text.props.height = style.GRID_CELL_SIZE
col.pack_start(cell_text, expand=False)
col.add_attribute(cell_text, 'text', 0)

cell_progress = Gtk.CellRendererProgress()
cell_progress.props.ypad = style.GRID_CELL_SIZE / 4
col.pack_start(cell_progress, expand=True)
col.add_attribute(cell_progress, 'value', 1)
col.add_attribute(cell_progress, 'pulse', 2)


if __name__ == '__main__':
    common.main(test)

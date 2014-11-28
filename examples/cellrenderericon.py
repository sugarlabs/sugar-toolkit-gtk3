from gi.repository import Gtk

from sugar3.graphics import style
from sugar3.graphics.icon import CellRendererIcon

import common


test = common.Test()
test.show()

model = Gtk.ListStore(str)
for icon in ['one', 'two', 'three']:
    model.append([icon])

treeview = Gtk.TreeView()
treeview.set_model(model)
test.pack_start(treeview, True, True, 0)
treeview.show()

col = Gtk.TreeViewColumn()
treeview.append_column(col)

cell_icon = CellRendererIcon()
cell_icon.props.width = style.GRID_CELL_SIZE
cell_icon.props.height = style.GRID_CELL_SIZE
cell_icon.props.size = style.SMALL_ICON_SIZE
cell_icon.props.icon_name = 'emblem-favorite'
col.pack_start(cell_icon, expand=False)

cell_text = Gtk.CellRendererText()
col.pack_start(cell_text, expand=True)
col.add_attribute(cell_text, 'text', 0)


if __name__ == '__main__':
    common.main(test)

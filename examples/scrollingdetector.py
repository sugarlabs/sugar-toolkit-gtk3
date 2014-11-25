import os
import time

from gi.repository import Gtk

from sugar3.graphics import style
from sugar3.graphics.icon import CellRendererIcon
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.scrollingdetector import ScrollingDetector
import common


test = common.Test()
test.show()

model = Gtk.ListStore(str)

data_dir = os.getenv('GTK_DATA_PREFIX', '/usr/')

iconlist = os.listdir(os.path.join(data_dir,
                      'share/icons/sugar/scalable/actions/'))
print "Displaying %s icons" % len(iconlist)
for icon in iconlist:
    icon = os.path.basename(icon)
    icon = icon[:icon.find('.')]
    model.append([icon])

scrolled = Gtk.ScrolledWindow()
scrolled.set_size_request(800, 800)
treeview = Gtk.TreeView()

treeview.set_model(model)
scrolled.add(treeview)
test.pack_start(scrolled, True, True, 0)
test.show_all()

col = Gtk.TreeViewColumn()
treeview.append_column(col)

xo_color = XoColor('#FF0000,#00FF00')
cell_icon = CellRendererIcon()
cell_icon.props.width = style.GRID_CELL_SIZE
cell_icon.props.height = style.GRID_CELL_SIZE
cell_icon.props.size = style.STANDARD_ICON_SIZE
cell_icon.props.xo_color = xo_color

col.pack_start(cell_icon, expand=False)
col.add_attribute(cell_icon, 'icon-name', 0)
cell_text = Gtk.CellRendererText()
col.pack_start(cell_text, expand=True)
col.add_attribute(cell_text, 'text', 0)

detector = ScrollingDetector(scrolled)
detector.connect_treeview(treeview)

if __name__ == '__main__':
    time_ini = time.time()
    common.main(test)

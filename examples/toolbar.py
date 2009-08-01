import gtk

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toolbarbox import ToolbarBox, ToolbarButton
from sugar.graphics import style

window = gtk.Window()

box = gtk.VBox()
window.add(box)

toolbar = ToolbarBox()
box.pack_start(toolbar, False)

tollbarbutton_1 = ToolbarButton(
        page=gtk.Button('sub-widget #1'),
        icon_name='computer-xo')
toolbar.toolbar.insert(tollbarbutton_1, -1)

tollbarbutton_2 = ToolbarButton(
        page=gtk.Button('sub-widget #2'),
        icon_name='button_cancel',
        tooltip='with custom palette instead of sub-widget')
toolbar.toolbar.insert(tollbarbutton_2, -1)

toolbar.toolbar.insert(gtk.SeparatorToolItem(), -1)

def del_cb(widget):
    toolbar.toolbar.remove(tollbarbutton_3)
del_b = gtk.Button('delete sub-widget #3')
del_b.connect('clicked', del_cb)
tollbarbutton_3 = ToolbarButton(
        page=del_b,
        icon_name='activity-journal')
toolbar.toolbar.insert(tollbarbutton_3, -1)

subbar = gtk.Toolbar()
subbutton = ToolButton(
        icon_name='document-send',
        tooltip='document-send')
subbar.insert(subbutton, -1)
subbar.show_all()

tollbarbutton_4 = ToolbarButton(
        page=subbar,
        icon_name='document-save')
toolbar.toolbar.insert(tollbarbutton_4, -1)

window.show_all()
gtk.main()

import gtk

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toolbar import Toolbar, ToolbarButton
from sugar.graphics import style

window = gtk.Window()

box = gtk.VBox()
window.add(box)

toolbar = Toolbar()
box.pack_start(toolbar, False)

tollbarbutton_1 = ToolbarButton(
        page=gtk.Button('sub-widget #1'),
        icon_name='computer-xo')
toolbar.top.insert(tollbarbutton_1, -1)

tollbarbutton_2 = ToolbarButton(
        page=gtk.Button('sub-widget #2'),
        icon_name='button_cancel',
        tooltip='with custom palette instead of sub-widget')
toolbar.top.insert(tollbarbutton_2, -1)

toolbar.top.insert(gtk.SeparatorToolItem(), -1)

def del_cb(widget):
    toolbar.top.remove(tollbarbutton_3)
del_b = gtk.Button('delete sub-widget #3')
del_b.connect('clicked', del_cb)
tollbarbutton_3 = ToolbarButton(
        page=del_b,
        icon_name='activity-journal')
toolbar.top.insert(tollbarbutton_3, -1)

subbar = gtk.Toolbar()
subbutton = ToolButton(
        icon_name='document-send',
        tooltip='document-send')
subbar.insert(subbutton, -1)
subbar.show_all()

tollbarbutton_4 = ToolbarButton(
        page=subbar,
        icon_name='document-save')
toolbar.top.insert(tollbarbutton_4, -1)

print [i.props.page for i in toolbar.subs]

window.show_all()
gtk.main()

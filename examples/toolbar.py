import gtk
from sugar.graphics.toolbar import Toolbar, ToolbarButton

window = gtk.Window()

box = gtk.VBox()
window.add(box)

toolbar = Toolbar()
box.pack_start(toolbar, False)

tollbarbutton_1 = ToolbarButton(toolbar, gtk.Button('sub-widget #1'),
        icon_name='computer-xo',
        tooltip='foo')
toolbar.top.insert(tollbarbutton_1, -1)

toolbar.top.insert(gtk.SeparatorToolItem(), -1)

tollbarbutton_2 = ToolbarButton(toolbar, gtk.Button('sub-widget #2'),
        icon_name='button_cancel',
        tooltip='foo')
toolbar.top.insert(tollbarbutton_2, -1)

toolbar.top.insert(gtk.SeparatorToolItem(), -1)

def del_cb(widget):
    toolbar.top.remove(tollbarbutton_3)
del_b = gtk.Button('delete sub-widget #3')
del_b.connect('clicked', del_cb)
tollbarbutton_3 = ToolbarButton(toolbar, del_b,
        icon_name='activity-journal',
        tooltip='del')
toolbar.top.insert(tollbarbutton_3, -1)

window.show_all()
gtk.main()

#!/usr/bin/python
from gi.repository import Gtk


import common
test = common.Test()
test.show()


class MyBox(Gtk.VBox):

    def __init__(self):
        Gtk.VBox.__init__(self)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.AUTOMATIC,
                                 Gtk.PolicyType.AUTOMATIC)

        self.store = Gtk.ListStore(str, str)
        for i in range(5):
            self.store.append([str(i), 'Item %s' % i])

        self.treeview = Gtk.TreeView(self.store)
        renderer_no_sens = Gtk.CellRendererText()
        # set 'sensitive' property
        renderer_no_sens.set_property('sensitive', False)

        renderer = Gtk.CellRendererText()

        column = Gtk.TreeViewColumn('\'sensitive\' False',
                                    renderer_no_sens, text=0)
        self.treeview.append_column(column)

        column = Gtk.TreeViewColumn('\'sensitive\' True',
                                    renderer, text=1)
        self.treeview.append_column(column)

        self.scrolled.add(self.treeview)
        self.add(self.scrolled)

        self.show_all()

vbox = MyBox()
test.pack_start(vbox, True, True, 0)
vbox.show()

if __name__ == '__main__':
    common.main(test)

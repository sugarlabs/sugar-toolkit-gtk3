#!/usr/bin/python
from gi.repository import Gtk

import common
test = common.Test()
test.show()


class MyBox(Gtk.Box):

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC,
                            Gtk.PolicyType.AUTOMATIC)

        store = Gtk.ListStore(str, str)
        for i in range(5):
            store.append([str(i), 'Item %s' % i])

        treeview = Gtk.TreeView(store)
        renderer_no_sens = Gtk.CellRendererText()
        # set 'sensitive' property
        renderer_no_sens.set_property('sensitive', False)

        renderer = Gtk.CellRendererText()

        column = Gtk.TreeViewColumn('\'sensitive\' False',
                                    renderer_no_sens, text=0)
        treeview.append_column(column)

        column = Gtk.TreeViewColumn('\'sensitive\' True',
                                    renderer, text=1)
        treeview.append_column(column)

        scrolled.add(treeview)
        self.pack_start(scrolled, True, True, 0)

        self.show_all()


box = MyBox()
test.pack_start(box, True, True, 0)
box.show()

if __name__ == '__main__':
    common.main(test)

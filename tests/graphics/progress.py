from gi.repository import Gtk

import common


test = common.Test()
test.show()

box = Gtk.HBox()
test.pack_start(box, True, False, 10)
box.show()

bar = Gtk.ProgressBar()
bar.set_fraction(0.5)
box.pack_start(bar, True, True, 10)
bar.show()


if __name__ == '__main__':
    common.main(test)

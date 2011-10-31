from gi.repository import Gtk

from sugar3.graphics import iconentry

def _destroy_cb(widget, data=None):
    Gtk.main_quit()

def __go_next_cb(entry, icon_pos, data=None):
    print 'Go next'

def __entry_activate_cb(widget, data=None):
    print 'Entry activate'

w = Gtk.Window()
w.connect("destroy", _destroy_cb)

box = Gtk.VBox()
w.add(box)

entry = iconentry.IconEntry()
entry.set_icon_from_name(iconentry.ICON_ENTRY_SECONDARY,
                         'go-next')
entry.connect('icon-press', __go_next_cb)
entry.connect('activate', __entry_activate_cb)
entry.set_progress_fraction(0.3)
box.pack_start(entry, False, False, 0)

w.show_all()

Gtk.main()

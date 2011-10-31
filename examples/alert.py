from gi.repository import Gtk

from sugar3.graphics.alert import Alert, TimeoutAlert

def _destroy_cb(widget, data=None):
    Gtk.main_quit()

def __start_response_cb(widget, data=None):
    print 'Response: start download'

w = Gtk.Window()
w.connect("destroy", _destroy_cb)

box = Gtk.VBox()
w.add(box)

alert = TimeoutAlert(9)
alert.props.title = 'Download started'
alert.props.msg = 'Sugar'
box.pack_start(alert, False, False, 0)
alert.connect('response', __start_response_cb)

w.show_all()

Gtk.main()

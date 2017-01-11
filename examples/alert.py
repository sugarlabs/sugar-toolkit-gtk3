from gi.repository import Gtk
from sugar3.graphics.alert import TimeoutAlert
from common import set_theme
set_theme()


def __start_response_cb(widget, data=None):
    print 'Response: start download'


w = Gtk.Window()
w.connect("delete-event", Gtk.main_quit)

box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
w.add(box)

alert = TimeoutAlert(9)
alert.props.title = 'Download started'
alert.props.msg = 'Sugar'
box.pack_start(alert, False, False, 0)
alert.connect('response', __start_response_cb)

w.show_all()

Gtk.main()

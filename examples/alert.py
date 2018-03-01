from gi.repository import Gtk
from sugar3.graphics.alert import TimeoutAlert
from common import set_theme


set_theme()
w = Gtk.Window()
w.connect("delete-event", Gtk.main_quit)
box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
w.add(box)

# Create a TimeoutAlert Object
alert = TimeoutAlert(5)
alert.props.title = '<Alert Title>'
alert.props.msg = '<Alert Message>'

# Add Timeout Object to the box
box.pack_start(alert, False, False, 0)


# Called when an alert object throws a response event.
def __alert_response_cb(alert, response_id):
    if response_id is Gtk.ResponseType.OK:
        print('Continue Button was clicked.')
    elif response_id is Gtk.ResponseType.CANCEL:
        print('Cancel Button was clicked.')
    elif response_id == -1:
        print('Timeout occurred')


alert.connect('response', __alert_response_cb)
w.show_all()
Gtk.main()

from gi.repository import Gtk

from sugar3.graphics.icon import EventIcon
from sugar3.graphics.icon import Icon

import common


test = common.Test()
test.show()

vbox = Gtk.VBox()
test.pack_start(vbox, True, True, 0)
vbox.show()

icon = Icon(icon_name="network-wireless-000")
icon.props.badge_name = 'emblem-favorite'
vbox.pack_start(icon, False, False, 0)
icon.show()

icon = EventIcon(icon_name="network-wireless-000")
icon.props.badge_name = 'emblem-favorite'
vbox.pack_start(icon, False, False, 0)
icon.show()


if __name__ == '__main__':
    common.main(test)

from gi.repository import Gtk

from sugar3.graphics.icon import EventIcon
from sugar3.graphics.icon import Icon
from sugar3.graphics import style
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.palette import Palette

import common


test = common.Test()
test.show()

box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
test.pack_start(box, True, True, 0)
box.show()

# An XO Icon, normal size, setting the color via the XoColor object
icon = Icon(icon_name='computer-xo',
            pixel_size=style.STANDARD_ICON_SIZE,
            xo_color=XoColor('#00BEFF,#FF7800'))
box.pack_start(icon, False, False, 0)
icon.show()

# You can mix constructor keyword argument and setting
# properties after creation
icon = EventIcon(icon_name='network-wireless-080',
                 pixel_size=style.STANDARD_ICON_SIZE)
# Badges are little icons displayed
icon.props.badge_name = 'emblem-favorite'
# Instead of using the XoColor, you can use any SVG color specifier:
icon.props.fill_color = 'rgb(230, 0, 10)'
icon.props.stroke_color = '#78E600'
# Unlike normal icons, EventIcons support palettes:
icon.props.palette = Palette('Hello World')
box.pack_start(icon, False, False, 0)
icon.show()


if __name__ == '__main__':
    common.main(test)

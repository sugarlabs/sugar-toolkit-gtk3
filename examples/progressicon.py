from gi.repository import Gtk
from gi.repository import GLib

from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.progressicon import ProgressIcon
from sugar3.graphics import style

import common


test = common.Test()

box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
test.pack_start(box, True, True, 0)

toolbar_box = ToolbarBox()
box.pack_start(toolbar_box, False, False, 0)

separator = Gtk.SeparatorToolItem()
toolbar_box.toolbar.insert(separator, -1)

icon = ProgressIcon(
    pixel_size=style.LARGE_ICON_SIZE,
    icon_name='computer-xo',
    stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
    fill_color=style.COLOR_WHITE.get_svg())
test.pack_start(icon, True, True, 0)
icon.show()

icon2 = ProgressIcon(
    pixel_size=style.LARGE_ICON_SIZE,
    icon_name='computer-xo',
    stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
    fill_color=style.COLOR_WHITE.get_svg(),
    direction='horizontal')
test.pack_start(icon2, True, True, 0)
icon2.show()

test.show_all()

progress = 0


def timeout_cb():
    global progress
    progress += 0.05
    icon.update(progress)
    icon2.update(progress)
    if progress >= 1:
        return False
    return True


GLib.timeout_add(50, timeout_cb)


if __name__ == '__main__':
    common.main(test)

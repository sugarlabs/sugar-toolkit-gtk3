# Copyright (C) 2007, Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Test the sugar3.graphics.icon.Icon widget.
"""

from gi.repository import Gtk

from sugar3.graphics.icon import Icon
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics import style

import common

test = common.Test()

box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
test.pack_start(box, True, True, 0)
sensitive_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
insensitive_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

box.pack_start(sensitive_box, True, True, 0)
box.pack_start(insensitive_box, True, True, 0)
box.show_all()


def create_icon_widgets(box, sensitive=True):
    icon = Icon(icon_name='go-previous')
    icon.props.pixel_size = style.STANDARD_ICON_SIZE
    box.pack_start(icon, True, True, 0)
    icon.set_sensitive(sensitive)
    icon.show()

    icon = Icon(icon_name='computer-xo',
                pixel_size=style.STANDARD_ICON_SIZE,
                xo_color=XoColor())
    box.pack_start(icon, True, True, 0)
    icon.set_sensitive(sensitive)
    icon.show()

    icon = Icon(icon_name='battery-000',
                pixel_size=style.STANDARD_ICON_SIZE,
                badge_name='emblem-busy')
    box.pack_start(icon, True, True, 0)
    icon.set_sensitive(sensitive)
    icon.show()

    icon = Icon(icon_name='gtk-new',
                pixel_size=style.STANDARD_ICON_SIZE,
                badge_name='gtk-cancel')
    box.pack_start(icon, True, True, 0)
    icon.set_sensitive(sensitive)
    icon.show()


create_icon_widgets(sensitive_box, True)
create_icon_widgets(insensitive_box, False)

test.show()

# This can be used to test for leaks by setting the LRU cache size
# in icon.py to 1.
# def idle_cb():
#     import gc
#     gc.collect()
#     test.queue_draw()
#     return True
#
# from gi.repository import GLib
# GLib.idle_add(idle_cb)

if __name__ == '__main__':
    common.main(test)

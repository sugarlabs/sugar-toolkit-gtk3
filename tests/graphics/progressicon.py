# Copyright (C) 2013, One Laptop Per Child
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
Test the sugar3.graphics.progressicon.ProgressIcon widget.
"""


from gi.repository import GLib

from sugar3.graphics.progressicon import ProgressIcon
from sugar3.graphics import style

import common

test = common.Test()
test.show()

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

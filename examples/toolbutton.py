from gi.repository import Gtk

from sugar3.graphics.icon import Icon
from sugar3.graphics.toolbutton import ToolButton

import common


test = common.Test()
test.show()

tb1 = ToolButton()
tb1.show()

tb2 = ToolButton('activity-start')
tb2.show()

Gtk.main()

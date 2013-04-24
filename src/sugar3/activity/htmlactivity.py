# Copyright (C) 2013 Daniel Narvaez
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

import os

from gi.repository import Gtk
from gi.repository import WebKit2

from sugar3.activity import activity


class HTMLActivity(activity.Activity):
    def __init__(self, handle):
        activity.Activity.__init__(self, handle)

        scrolled_window = Gtk.ScrolledWindow()

        self._web_view = WebKit2.WebView()
        scrolled_window.add(self._web_view)
        self._web_view.show()

        index_path = os.path.join(activity.get_bundle_path(), "index.html")
        self._web_view.load_uri('file://' + index_path)

        self.set_canvas(scrolled_window)
        scrolled_window.show()


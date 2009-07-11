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

import gtk
import gobject
import logging
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE

from sugar.graphics import style
from sugar.graphics.toolbutton import ToolButton

class ToolbarButton(ToolButton):
    def __init__(self, bar, page, expand_bg=style.TOOLBAR_COLOR, **kwargs):
        ToolButton.__init__(self, **kwargs)

        self.modify_bg(gtk.STATE_NORMAL, expand_bg.get_gdk_color())

        self._bar = bar
        self._page = _align(_Box, page, bar._hpad, style._FOCUS_LINE_WIDTH*3,
                expand_bg)
        self._page._toolitem = self
        page.show()

        bar._notebook.append_page(self._page)

        self.connect('clicked',
                lambda widget: self.set_expanded(not self.expanded))
        self.connect('destroy', self.__destroy_cb)

    def __destroy_cb(self, widget):
        self._bar._remove_page(self._page)

    def get_expanded(self):
        return self._bar._expanded_page() == self._page

    def set_expanded(self, value):
        if self.get_expanded() == value:
            return
        if value:
            expanded = self._bar._expanded_page()
            if expanded:
                expanded._toolitem.window.invalidate_rect(None, True)
            self._page._toolitem_alloc = self.allocation
            self._bar._expand_page(self._page)
        else:
            self._bar._shrink_page()

    expanded = property(get_expanded, set_expanded)

    def do_expose_event(self, event):
        child = self.get_child()
        alloc = self.allocation

        if not self.expanded or self.palette and self.palette.is_up():
            ToolButton.do_expose_event(self, event)
            _paint_arrow(self, event, gtk.ARROW_UP)
            return

        self.get_style().paint_box(event.window,
                gtk.STATE_NORMAL, gtk.SHADOW_IN, event.area, self,
                'palette-invoker', alloc.x, -style._FOCUS_LINE_WIDTH,
                alloc.width, alloc.height + style._FOCUS_LINE_WIDTH*2)

        if child.state != gtk.STATE_PRELIGHT:
            self.get_style().paint_box(event.window,
                    gtk.STATE_NORMAL, gtk.SHADOW_NONE, event.area, self, None,
                    alloc.x + style._FOCUS_LINE_WIDTH, 0,
                    alloc.width - style._FOCUS_LINE_WIDTH*2, alloc.height)

        gtk.ToolButton.do_expose_event(self, event)
        _paint_arrow(self, event, gtk.ARROW_DOWN)

class Toolbar(gtk.VBox):
    __gsignals__ = {
        'current-toolbar-changed': (SIGNAL_RUN_FIRST, TYPE_NONE, ([int]))
        }

    def __init__(self, hpad=style.TOOLBOX_HORIZONTAL_PADDING):
        gtk.VBox.__init__(self)

        self._bar = gtk.Toolbar()
        self._hpad = hpad
        toolbar = _align(gtk.EventBox, self._bar, hpad, 0,
                style.COLOR_TOOLBAR_GREY)
        self.pack_start(toolbar)

        self._notebook = gtk.Notebook()
        self._notebook.set_show_border(False)
        self._notebook.set_show_tabs(False)
        self._notebook.show()

        self._notebook.connect('notify::page', lambda notebook, pspec:
                self.emit('current-toolbar-changed', notebook.props.page))

    top = property(lambda self: self._bar)

    def _remove_page(self, page):
        page = self._notebook.page_num(page)
        self._notebook.remove_page(page)

    def _expanded_page(self):
        if self._notebook.parent is None:
            return None
        page_no = self._notebook.get_current_page()
        return self._notebook.get_nth_page(page_no)

    def _shrink_page(self):
        self.remove(self._notebook)

    def _expand_page(self, page):
        page_no = self._notebook.page_num(page)
        self._notebook.set_current_page(page_no)

        if self._notebook.parent is None:
            self.pack_start(self._notebook)

class _Box(gtk.EventBox):
    def __init__(self):
        gtk.EventBox.__init__(self)
        self._toolitem_alloc = gtk.gdk.Rectangle()
        self.connect('expose-event', self.do_expose_event)
        self.set_app_paintable(True)

    def do_expose_event(self, widget, event):
        self.get_style().paint_box(event.window,
                gtk.STATE_NORMAL, gtk.SHADOW_IN, event.area, self,
                'palette-invoker', -style._FOCUS_LINE_WIDTH, 0,
                self.allocation.width + style._FOCUS_LINE_WIDTH*2,
                self.allocation.height + style._FOCUS_LINE_WIDTH)
        self.get_style().paint_box(event.window,
                gtk.STATE_NORMAL, gtk.SHADOW_NONE, event.area, self, None,
                self._toolitem_alloc.x + style._FOCUS_LINE_WIDTH, 0,
                self._toolitem_alloc.width - style._FOCUS_LINE_WIDTH*2,
                style._FOCUS_LINE_WIDTH)

def _align(box_class, widget, hpad, vpad, color):
    widget.modify_bg(gtk.STATE_NORMAL, color.get_gdk_color())

    if hpad or vpad:
        top_pad = vpad
        bottom_pad = vpad and vpad - style._FOCUS_LINE_WIDTH
        alignment = gtk.Alignment(0.0, 0.0, 1.0, 1.0)
        alignment.set_padding(top_pad, bottom_pad, hpad, hpad)
        alignment.add(widget)
        alignment.show()
    else:
        alignment = widget

    box = box_class()
    box.modify_bg(gtk.STATE_NORMAL, color.get_gdk_color())
    box.modify_bg(gtk.STATE_PRELIGHT, color.get_gdk_color())
    box.modify_bg(gtk.STATE_ACTIVE, style.COLOR_BUTTON_GREY.get_gdk_color())
    box.add(alignment)
    box.show()

    return box

def _paint_arrow(widget, event, type):
    a = widget.allocation
    widget.get_style().paint_arrow(event.window,
            gtk.STATE_NORMAL, gtk.SHADOW_IN, event.area, widget,
            None, type,  True,
            a.x + a.width/2 - style.TOOLBAR_ARROW_SIZE/2,
            a.y + a.height - style.TOOLBAR_ARROW_SIZE - style._FOCUS_LINE_WIDTH,
            style.TOOLBAR_ARROW_SIZE, style.TOOLBAR_ARROW_SIZE)

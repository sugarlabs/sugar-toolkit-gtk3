# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
# Copyright (C) 2008, One Laptop Per Child
# Copyright (C) 2009, Tomeu Vizoso
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
STABLE.
"""

import gtk
import gobject
import pango

from sugar.graphics import palettegroup
from sugar.graphics import animator
from sugar.graphics import style
from sugar.graphics.icon import Icon
from sugar.graphics.palettewindow import PaletteWindow
from sugar import _sugarext

# DEPRECATED
# Import these for backwards compatibility
from sugar.graphics.palettewindow import MouseSpeedDetector, Invoker, \
        WidgetInvoker, CanvasInvoker, ToolInvoker, CellRendererInvoker


class Palette(PaletteWindow):
    PRIMARY = 0
    SECONDARY = 1

    __gtype_name__ = 'SugarPalette'

    def __init__(self, label=None, accel_path=None, menu_after_content=False,
                 text_maxlen=60, **kwargs):
        # DEPRECATED: label is passed with the primary-text property,
        # accel_path is set via the invoker property, and menu_after_content
        # is not used

        self._primary_text = None
        self._secondary_text = None
        self._icon = None
        self._icon_visible = True
        self._palette_state = self.PRIMARY

        palette_box = gtk.VBox()

        primary_box = gtk.HBox()
        palette_box.pack_start(primary_box, expand=False)
        primary_box.show()

        self._icon_box = gtk.HBox()
        self._icon_box.set_size_request(style.GRID_CELL_SIZE, -1)
        primary_box.pack_start(self._icon_box, expand=False)

        labels_box = gtk.VBox()
        self._label_alignment = gtk.Alignment(xalign=0, yalign=0.5,
                                              xscale=1, yscale=0.33)
        self._label_alignment.set_padding(0, 0, style.DEFAULT_SPACING,
                                          style.DEFAULT_SPACING)
        self._label_alignment.add(labels_box)
        self._label_alignment.show()
        primary_box.pack_start(self._label_alignment, expand=True)
        labels_box.show()

        self._label = gtk.AccelLabel('')
        self._label.set_alignment(0, 0.5)

        if text_maxlen > 0:
            self._label.set_max_width_chars(text_maxlen)
            self._label.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        labels_box.pack_start(self._label, expand=True)

        self._secondary_label = gtk.Label()
        self._secondary_label.set_alignment(0, 0.5)

        if text_maxlen > 0:
            self._secondary_label.set_max_width_chars(text_maxlen)
            self._secondary_label.set_ellipsize(pango.ELLIPSIZE_END)

        labels_box.pack_start(self._secondary_label, expand=True)

        self._secondary_box = gtk.VBox()
        palette_box.pack_start(self._secondary_box)

        self._separator = gtk.HSeparator()
        self._secondary_box.pack_start(self._separator)

        self._menu_content_separator = gtk.HSeparator()

        self._secondary_anim = animator.Animator(2.0, 10)
        self._secondary_anim.add(_SecondaryAnimation(self))

        # we init after initializing all of our containers
        PaletteWindow.__init__(self, **kwargs)

        primary_box.set_size_request(-1, style.GRID_CELL_SIZE
                                     - 2 * self.get_border_width())

        self._full_request = [0, 0]
        self._menu_box = None
        self._content = None

        # we set these for backward compatibility
        if label is not None:
            self.props.primary_text = label

        self._add_menu()
        self._secondary_box.pack_start(self._menu_content_separator)
        self._add_content()

        self.action_bar = PaletteActionBar()
        self._secondary_box.pack_start(self.action_bar)
        self.action_bar.show()

        self.add(palette_box)
        palette_box.show()

        # The menu is not shown here until an item is added
        self.menu = _Menu(self)
        self.menu.connect('item-inserted', self.__menu_item_inserted_cb)

        self.connect('realize', self.__realize_cb)
        self.connect('show', self.__show_cb)
        self.connect('hide', self.__hide_cb)
        self.connect('notify::invoker', self.__notify_invoker_cb)
        self.connect('destroy', self.__destroy_cb)

    def _invoker_right_click_cb(self, invoker):
        self.popup(immediate=True, state=self.SECONDARY)

    def do_style_set(self, previous_style):
        # Prevent a warning from pygtk
        if previous_style is not None:
            gtk.Window.do_style_set(self, previous_style)
        self.set_border_width(self.get_style().xthickness)

    def __menu_item_inserted_cb(self, menu):
        self._update_separators()

    def __destroy_cb(self, palette):
        self._secondary_anim.stop()
        self.popdown(immediate=True)
        # Break the reference cycle. It looks like the gc is not able to free
        # it, possibly because gtk.Menu memory handling is very special.
        self.menu.disconnect_by_func(self.__menu_item_inserted_cb)
        self.menu = None

    def __show_cb(self, widget):
        self.menu.set_active(True)

    def __hide_cb(self, widget):
        self.menu.set_active(False)
        self.menu.cancel()
        self._secondary_anim.stop()

    def __notify_invoker_cb(self, palette, pspec):
        invoker = self.props.invoker
        if invoker is not None and hasattr(invoker.props, 'widget'):
            self._update_accel_widget()
            self._invoker.connect('notify::widget',
                                  self.__invoker_widget_changed_cb)

    def __invoker_widget_changed_cb(self, invoker, spec):
        self._update_accel_widget()

    def get_full_size_request(self):
        return self._full_request

    def popup(self, immediate=False, state=None):
        if self._invoker is not None:
            self._update_full_request()

        PaletteWindow.popup(self, immediate)

        if state is None:
            state = self.PRIMARY
        self.set_palette_state(state)

        if state == self.PRIMARY:
            self._secondary_anim.start()
        else:
            self._secondary_anim.stop()

    def popdown(self, immediate=False):
        if immediate:
            self._secondary_anim.stop()
            self._popdown_submenus()
            # to suppress glitches while later re-opening
            self.set_palette_state(self.PRIMARY)
        PaletteWindow.popdown(self, immediate)

    def _popdown_submenus(self):
        # TODO explicit hiding of subitems
        # should be removed after fixing #1301
        if self.menu is not None:
            for menu_item in self.menu.get_children():
                if menu_item.props.submenu is not None:
                    menu_item.props.submenu.popdown()

    def on_enter(self, event):
        PaletteWindow.on_enter(self, event)
        self._secondary_anim.start()

    def _add_menu(self):
        self._menu_box = gtk.VBox()
        self._secondary_box.pack_start(self._menu_box)
        self._menu_box.show()

    def _add_content(self):
        # The content is not shown until a widget is added
        self._content = gtk.VBox()
        self._content.set_border_width(style.DEFAULT_SPACING)
        self._secondary_box.pack_start(self._content)

    def _update_accel_widget(self):
        assert self.props.invoker is not None
        self._label.props.accel_widget = self.props.invoker.props.widget

    def set_primary_text(self, label, accel_path=None):
        self._primary_text = label

        if label is not None:
            self._label.set_markup('<b>%s</b>' % label)
            self._label.show()

    def get_primary_text(self):
        return self._primary_text

    primary_text = gobject.property(type=str,
                                    getter=get_primary_text,
                                    setter=set_primary_text)

    def set_secondary_text(self, label):
        if label is not None:
            label = label.split('\n', 1)[0]
        self._secondary_text = label

        if label is None:
            self._secondary_label.hide()
        else:
            self._secondary_label.set_text(label)
            self._secondary_label.show()

    def get_secondary_text(self):
        return self._secondary_text

    secondary_text = gobject.property(type=str, getter=get_secondary_text,
        setter=set_secondary_text)

    def _show_icon(self):
        self._label_alignment.set_padding(0, 0, 0, style.DEFAULT_SPACING)
        self._icon_box.show()

    def _hide_icon(self):
        self._icon_box.hide()
        self._label_alignment.set_padding(0, 0, style.DEFAULT_SPACING,
                                          style.DEFAULT_SPACING)

    def set_icon(self, icon):
        if icon is None:
            self._icon = None
            self._hide_icon()
        else:
            if self._icon:
                self._icon_box.remove(self._icon_box.get_children()[0])

            event_box = gtk.EventBox()
            event_box.connect('button-release-event',
                              self.__icon_button_release_event_cb)
            self._icon_box.pack_start(event_box)
            event_box.show()

            self._icon = icon
            self._icon.props.icon_size = gtk.ICON_SIZE_LARGE_TOOLBAR
            event_box.add(self._icon)
            self._icon.show()
            self._show_icon()

    def get_icon(self):
        return self._icon

    icon = gobject.property(type=object, getter=get_icon, setter=set_icon)

    def __icon_button_release_event_cb(self, icon, event):
        self.emit('activate')

    def set_icon_visible(self, visible):
        self._icon_visible = visible

        if visible and self._icon is not None:
            self._show_icon()
        else:
            self._hide_icon()

    def get_icon_visible(self):
        return self._icon_visilbe

    icon_visible = gobject.property(type=bool,
                                    default=True,
                                    getter=get_icon_visible,
                                    setter=set_icon_visible)

    def set_content(self, widget):
        if len(self._content.get_children()) > 0:
            self._content.remove(self._content.get_children()[0])

        if widget is not None:
            self._content.add(widget)
            self._content.show()
        else:
            self._content.hide()

        self._update_accept_focus()
        self._update_separators()

    def do_size_request(self, requisition):
        PaletteWindow.do_size_request(self, requisition)

        # gtk.AccelLabel request doesn't include the accelerator.
        label_width = self._label_alignment.size_request()[0] + \
                      self._label.get_accel_width() + \
                      2 * self.get_border_width()

        requisition.width = max(requisition.width,
                                label_width,
                                self._full_request[0])

    def _update_separators(self):
        visible = len(self.menu.get_children()) > 0 or  \
                  len(self._content.get_children()) > 0
        self._separator.props.visible = visible

        visible = len(self.menu.get_children()) > 0 and  \
                  len(self._content.get_children()) > 0
        self._menu_content_separator.props.visible = visible

    def _update_accept_focus(self):
        accept_focus = len(self._content.get_children())
        if self.window:
            self.window.set_accept_focus(accept_focus)

    def __realize_cb(self, widget):
        self._update_accept_focus()

    def _update_full_request(self):
        if self._palette_state == self.PRIMARY:
            self.menu.embed(self._menu_box)
            self._secondary_box.show()

        self._full_request = self.size_request()

        if self._palette_state == self.PRIMARY:
            self.menu.unembed()
            self._secondary_box.hide()

    def _set_palette_state(self, state):
        if self._palette_state == state:
            return

        if state == self.PRIMARY:
            self.menu.unembed()
            self._secondary_box.hide()
        elif state == self.SECONDARY:
            self.menu.embed(self._menu_box)
            self._secondary_box.show()
            self.update_position()

        self._palette_state = state


class PaletteActionBar(gtk.HButtonBox):

    def add_action(self, label, icon_name=None):
        button = gtk.Button(label)

        if icon_name:
            icon = Icon(icon_name)
            button.set_image(icon)
            icon.show()

        self.pack_start(button)
        button.show()


class _Menu(_sugarext.Menu):

    __gtype_name__ = 'SugarPaletteMenu'

    __gsignals__ = {
        'item-inserted': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
    }

    def __init__(self, palette):
        _sugarext.Menu.__init__(self)
        self._palette = palette

    def do_insert(self, item, position):
        _sugarext.Menu.do_insert(self, item, position)
        self.emit('item-inserted')
        self.show()

    def attach(self, child, left_attach, right_attach,
               top_attach, bottom_attach):
        _sugarext.Menu.attach(self, child, left_attach, right_attach,
                              top_attach, bottom_attach)
        self.emit('item-inserted')
        self.show()

    def do_expose_event(self, event):
        # Ignore the Menu expose, just do the MenuShell expose to prevent any
        # border from being drawn here. A border is drawn by the palette object
        # around everything.
        gtk.MenuShell.do_expose_event(self, event)

    def do_grab_notify(self, was_grabbed):
        # Ignore grab_notify as the menu would close otherwise
        pass

    def do_deactivate(self):
        self._palette.hide()


class _SecondaryAnimation(animator.Animation):

    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette.set_palette_state(Palette.SECONDARY)

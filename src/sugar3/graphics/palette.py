# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
# Copyright (C) 2008, One Laptop Per Child
# Copyright (C) 2009, Tomeu Vizoso
# Copyright (C) 2011, Benjamin Berg <benjamin@sipsolutions.net>
# Copyright (C) 2011, Marco Pesenti Gritti <marco@marcopg.org>
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

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Pango

from sugar3.graphics import animator
from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.palettewindow import PaletteWindow, \
    _PaletteWindowWidget, _PaletteMenuWidget
from sugar3.graphics.palettemenu import PaletteMenuItem

from sugar3.graphics.palettewindow import MouseSpeedDetector, Invoker, \
        WidgetInvoker, CursorInvoker, ToolInvoker, CellRendererInvoker
assert MouseSpeedDetector
assert Invoker
assert WidgetInvoker
assert CursorInvoker
assert ToolInvoker
assert CellRendererInvoker

class _HeaderItem(Gtk.MenuItem):
    """A MenuItem with a custom child widget that gets all the
    available space.

    """

    __gtype_name__ = 'SugarPaletteHeader'

    def __init__(self, widget):
        Gtk.MenuItem.__init__(self)
        if self.get_child() is not None:
            self.remove(self.get_child())
        self.add(widget)
        # FIXME we have to mark it as insensitive again to make it an
        # informational element, when we realize how to get the icon
        # displayed correctly - SL #3836
        # self.set_sensitive(False)

    def do_size_allocate(self, allocation):
        self.set_allocation(allocation)
        self.get_child().size_allocate(allocation)


class _HeaderSeparator(Gtk.SeparatorMenuItem):
    """A SeparatorMenuItem that can be styled in the theme."""

    __gtype_name__ = 'SugarPaletteHeaderSeparator'

    def __init__(self):
        Gtk.SeparatorMenuItem.__init__(self)


class Palette(PaletteWindow):
    """Floating palette implementation.

    This class dynamically switches between one of two encapsulated child
    widget types: a _PaletteWindowWidget or a _PaletteMenuWidget.

    The window widget, created by default, acts as the container for any
    type of widget the user may wish to add. It can optionally display primary
    text, secondary text, and an icon at the top of the palette.

    If the user attempts to access the 'menu' property, the window widget is
    destroyed and the palette is dynamically switched to use a menu widget.
    This is a GtkMenu that retains the same look and feel as a normal palette,
    allowing submenus and so on. If primary text, secondary text and/or icons
    were provided, an initial menu entry is created containing widgets to
    display such information.
    """

    __gsignals__ = {
        'activate': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    __gtype_name__ = 'SugarPalette'

    def __init__(self, label=None, accel_path=None,
                 text_maxlen=60, **kwargs):
        # DEPRECATED: label is passed with the primary-text property,
        # accel_path is set via the invoker property

        self._primary_text = None
        self._secondary_text = None
        self._icon = None
        self._icon_visible = True
        self._palette_state = self.PRIMARY

        self._primary_box = Gtk.HBox()
        self._primary_box.show()

        self._icon_box = Gtk.HBox()
        self._icon_box.set_size_request(style.GRID_CELL_SIZE, -1)
        self._primary_box.pack_start(self._icon_box, False, True, 0)

        labels_box = Gtk.VBox()
        self._label_alignment = Gtk.Alignment(xalign=0, yalign=0.5, xscale=1,
                                              yscale=0.33)
        self._label_alignment.set_padding(0, 0, style.DEFAULT_SPACING,
                                          style.DEFAULT_SPACING)
        self._label_alignment.add(labels_box)
        self._label_alignment.show()
        self._primary_box.pack_start(self._label_alignment, True, True, 0)
        labels_box.show()

        self._label = Gtk.AccelLabel(label='')
        self._label.set_alignment(0, 0.5)

        if text_maxlen > 0:
            self._label.set_max_width_chars(text_maxlen)
            self._label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        labels_box.pack_start(self._label, True, True, 0)

        self._secondary_label = Gtk.Label()
        self._secondary_label.set_alignment(0, 0.5)

        if text_maxlen > 0:
            self._secondary_label.set_max_width_chars(text_maxlen)
            self._secondary_label.set_ellipsize(Pango.EllipsizeMode.END)

        labels_box.pack_start(self._secondary_label, True, True, 0)

        self._secondary_box = Gtk.VBox()

        self._separator = Gtk.HSeparator()
        self._secondary_box.pack_start(self._separator, True, True, 0)

        self._secondary_anim = animator.Animator(2.0, 10)
        self._secondary_anim.add(_SecondaryAnimation(self))

        # we init after initializing all of our containers
        PaletteWindow.__init__(self, **kwargs)

        self._full_request = [0, 0]
        self._content = None

        # we set these for backward compatibility
        if label is not None:
            self.props.primary_text = label

        self._add_content()

        self.action_bar = PaletteActionBar()
        self._secondary_box.pack_start(self.action_bar, True, True, 0)
        self.action_bar.show()

        self.connect('notify::invoker', self.__notify_invoker_cb)
        self.connect('popdown', self.__popdown_cb)

        # Default to a normal window palette
        self._content_widget = None
        self.set_content(None)

    def _setup_widget(self):
        PaletteWindow._setup_widget(self)
        self._widget.connect('destroy', self.__destroy_cb)

    def __destroy_cb(self, palette):
        self._secondary_anim.stop()
        self.popdown(immediate=True)
        # Break the reference cycle. It looks like the gc is not able to free
        # it, possibly because Gtk.Menu memory handling is very special.
        self._widget = None

    def __popdown_cb(self, widget):
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
            # to suppress glitches while later re-opening
            self.set_palette_state(self.PRIMARY)
            if self._widget:
                self._widget.size_request()
        PaletteWindow.popdown(self, immediate)

    def on_enter(self):
        PaletteWindow.on_enter(self)
        self._secondary_anim.start()

    def _add_content(self):
        # The content is not shown until a widget is added
        self._content = Gtk.VBox()
        self._secondary_box.pack_start(self._content, True, True,
                                       style.DEFAULT_SPACING)

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

    primary_text = GObject.property(type=str,
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

    secondary_text = GObject.property(type=str, getter=get_secondary_text,
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

            event_box = Gtk.EventBox()
            event_box.connect('button-release-event',
                              self.__icon_button_release_event_cb)
            self._icon_box.pack_start(event_box, True, True, 0)
            event_box.show()

            self._icon = icon
            self._icon.props.icon_size = Gtk.IconSize.LARGE_TOOLBAR
            event_box.add(self._icon)
            self._icon.show()
            self._show_icon()

    def get_icon(self):
        return self._icon

    icon = GObject.property(type=object, getter=get_icon, setter=set_icon)

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

    icon_visible = GObject.property(type=bool,
                                    default=True,
                                    getter=get_icon_visible,
                                    setter=set_icon_visible)

    def set_content(self, widget):
        assert self._widget is None \
                or isinstance(self._widget, _PaletteWindowWidget)

        if self._widget is None:
            self._widget = _PaletteWindowWidget(self)
            self._setup_widget()

            self._palette_box = Gtk.VBox()
            self._palette_box.pack_start(self._primary_box, False, True, 0)
            self._palette_box.pack_start(self._secondary_box, True, True, 0)

            self._widget.add(self._palette_box)
            self._palette_box.show()
            height = style.GRID_CELL_SIZE - 2 * self._widget.get_border_width()
            self._primary_box.set_size_request(-1, height)

        if self._content.get_children():
            self._content.remove(self._content.get_children()[0])

        if widget is not None:
            widget.connect('button-release-event',
                           self.__widget_button_release_cb)
            self._content.add(widget)
            self._content.show()
        else:
            self._content.hide()

        self._content_widget = widget

        self._update_accept_focus()
        self._update_separators()

    def __widget_button_release_cb(self, widget, event):
        event_widget = Gtk.get_event_widget(event)
        if isinstance(event_widget, PaletteMenuItem):
            self.popdown(immediate=True)
        return False

    def get_label_width(self):
        # Gtk.AccelLabel request doesn't include the accelerator.
        label_width = self._label_alignment.get_preferred_width()[1] + \
                      self._label.get_accel_width()
        return label_width

    def _update_separators(self):
        visible = self._content.get_children()
        self._separator.props.visible = visible

    def _update_accept_focus(self):
        accept_focus = len(self._content.get_children())
        self._widget.set_accept_focus(accept_focus)

    def _update_full_request(self):
        if self._palette_state == self.PRIMARY:
            self._secondary_box.show()

        self._full_request = self._widget.size_request()

        if self._palette_state == self.PRIMARY:
            self._secondary_box.hide()

    def _set_palette_state(self, state):
        if self._palette_state == state:
            return

        if state == self.PRIMARY:
            self._secondary_box.hide()
        elif state == self.SECONDARY:
            self._secondary_box.show()
            self.update_position()

        self._palette_state = state

    def get_menu(self):
        assert self._content_widget is None

        if self._widget is None \
                or not isinstance(self._widget, _PaletteMenuWidget):
            if self._widget is not None:
                self._palette_box.remove(self._primary_box)
                self._palette_box.remove(self._secondary_box)
                self._teardown_widget()
                self._widget.destroy()

            self._widget = _PaletteMenuWidget()

            self._label_menuitem = _HeaderItem(self._primary_box)
            self._label_menuitem.show()
            self._widget.append(self._label_menuitem)

            separator = _HeaderSeparator()
            self._widget.append(separator)
            separator.show()

            self._setup_widget()

        return self._widget

    menu = GObject.property(type=object, getter=get_menu)


class PaletteActionBar(Gtk.HButtonBox):

    def add_action(self, label, icon_name=None):
        button = Gtk.Button(label)

        if icon_name:
            icon = Icon(icon_name)
            button.set_image(icon)
            icon.show()

        self.pack_start(button, True, True, 0)
        button.show()


class _SecondaryAnimation(animator.Animation):

    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette.set_palette_state(Palette.SECONDARY)

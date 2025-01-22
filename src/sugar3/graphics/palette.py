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
import textwrap

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango

from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.palettewindow import PaletteWindow, \
    _PaletteWindowWidget, _PaletteMenuWidget
from sugar3.graphics.palettemenu import PaletteMenuItem

from sugar3.graphics.palettewindow import MouseSpeedDetector, Invoker, \
    WidgetInvoker, CursorInvoker, ToolInvoker, TreeViewInvoker

assert MouseSpeedDetector
assert Invoker
assert WidgetInvoker
assert CursorInvoker
assert ToolInvoker
assert TreeViewInvoker



class _HeaderItem(Gtk.ListBoxRow):
    """A ListBoxRow with a custom child widget that gets all the
    available space.
    """

    __gtype_name__ = 'SugarPaletteHeader'

    def __init__(self, widget):
        super().__init__()
        self.add(widget)
        # FIXME we have to mark it as insensitive again to make it an
        # informational element, when we realize how to get the icon
        # displayed correctly - SL #3836
        # self.set_sensitive(False)

    def do_size_allocate(self, allocation):
        self.set_allocation(allocation)
        self.get_child().size_allocate(allocation)

    def do_draw(self, cr):
        # force state normal, we don't want change color when hover
        self.set_state_flags(Gtk.StateFlags.NORMAL, clear=True)

        # draw separator
        allocation = self.get_allocation()
        cr.save()
        line_width = 2
        cr.set_line_width(line_width)
        cr.set_source_rgb(.5, .5, .5)  # button_grey #808080;
        cr.move_to(0, allocation.height - line_width)
        cr.line_to(allocation.width, allocation.height - line_width)
        cr.stroke()
        cr.restore()

        # draw content
        super().do_draw(cr)
        return False



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
                 text_maxlen=style.MENU_WIDTH_CHARS, **kwargs):
        # DEPRECATED: label is passed with the primary-text property,
        # accel_path is set via the invoker property

        self._primary_text = None
        self._secondary_text = None
        self._icon = None
        self._icon_visible = True

        self._primary_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._primary_box.set_visible(True)

        self._icon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._icon_box.set_size_request(style.GRID_CELL_SIZE, -1)
        self._primary_box.append(self._icon_box)

        labels_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._label_alignment = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._label_alignment.set_margin_start(style.DEFAULT_SPACING)
        self._label_alignment.set_margin_end(style.DEFAULT_SPACING)
        self._label_alignment.set_margin_top(style.DEFAULT_SPACING)
        self._label_alignment.set_margin_bottom(style.DEFAULT_SPACING)
        self._label_alignment.append(labels_box)
        self._label_alignment.set_visible(True)
        self._primary_box.append(self._label_alignment)
        labels_box.set_visible(True)

        self._label = Gtk.AccelLabel(label='')
        self._label.set_xalign(0)
        self._label.set_yalign(0.5)

        if text_maxlen > 0:
            self._label.set_max_width_chars(text_maxlen)
            self._label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
        labels_box.append(self._label)

        self._primary_box.connect('button-release-event',
                                  self.__button_release_event_cb)
        self._primary_box.set_events(Gdk.EventMask.BUTTON_RELEASE_MASK)

        self._secondary_label = Gtk.Label()
        self._secondary_label.set_xalign(0)
        self._secondary_label.set_yalign(0.5)
        labels_box.append(self._secondary_label)

        self._secondary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self._separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self._secondary_box.append(self._separator)
        self._secondary_box.set_visible(True)

        # we init after initializing all of our containers
        PaletteWindow.__init__(self, **kwargs)

        self._full_request = [0, 0]
        self._content = None

        # we set these for backward compatibility
        if label is not None:
            self.props.primary_text = label

        self._add_content()

        self.action_bar = PaletteActionBar()
        self._secondary_box.append(self.action_bar)
        self.action_bar.set_visible(True)

        self.connect('notify::invoker', self.__notify_invoker_cb)

        # Default to a normal window palette
        self._content_widget = None
        self.set_content(None)

    def _setup_widget(self):
        PaletteWindow._setup_widget(self)
        self._widget.connect('destroy', self.__destroy_cb)
        self._widget.connect('map', self.__map_cb)

    def __map_cb(self, *args):
        # Fixes #4463
        if hasattr(self._widget, 'present'):
            self._widget.present()

    def __destroy_cb(self, palette):
        self.popdown(immediate=True)
        # Break the reference cycle. It looks like the gc is not able to free
        # it, possibly because Gtk.Menu memory handling is very special.
        self._widget = None

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

    def popup(self, immediate=False):
        if self._invoker is not None:
            self._update_full_request()

        PaletteWindow.popup(self, immediate)

    def popdown(self, immediate=False, state=None):
        '''
        Popdown (or show the full contents of) the palette.

        Keyword Args:
            immediate (bool): if True, the palette will be shown instantly (as
                if the user right clicked the item).  If False, the palette
                will be shown after the usual activation wait time.

        .. deprecated:: 0.109
            The state keyword argument is deprecated.  The old
            secondary state has become the only state.
        '''
        if immediate:
            if self._widget:
                self._widget.size_request()
        PaletteWindow.popdown(self, immediate)

    def on_enter(self):
        PaletteWindow.on_enter(self)

    def _add_content(self):
        # The content is not shown until a widget is added
        self._content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._secondary_box.append(self._content)
        self._content.set_margin_top(style.DEFAULT_SPACING)
        self._content.set_visible(True)

    def _update_accel_widget(self):
        assert self.props.invoker is not None
        self._label.props.accel_widget = self.props.invoker.props.widget

    def set_primary_text(self, label, accel_path=None):
        self._primary_text = label
        if label is not None:
            label = GLib.markup_escape_text(label)
            self._label.set_markup('<b>%s</b>' % label)
            self._label.set_visible(True)

    def get_primary_text(self):
        return self._primary_text

    primary_text = GObject.Property(type=str,
                                    getter=get_primary_text,
                                    setter=set_primary_text)

    def __button_release_event_cb(self, widget, event):
        if self.props.invoker is not None:
            self.props.invoker.primary_text_clicked()

    def set_secondary_text(self, label):
        if label is None:
            self._secondary_label.set_visible(False)
        else:
            NO_OF_LINES = 3
            ELLIPSIS_LENGTH = 6

            label = label.replace('\n', ' ')
            label = label.replace('\r', ' ')

            if hasattr(self._secondary_label, 'set_lines'):
                self._secondary_label.set_max_width_chars(
                    style.MENU_WIDTH_CHARS)
                self._secondary_label.set_line_wrap(True)
                self._secondary_label.set_ellipsize(
                    style.ELLIPSIZE_MODE_DEFAULT)
                self._secondary_label.set_line_wrap_mode(
                    Pango.WrapMode.WORD_CHAR)
                self._secondary_label.set_lines(NO_OF_LINES)
                self._secondary_label.set_justify(Gtk.Justification.FILL)
            else:
                # FIXME: fallback for Gtk < 3.10
                body_width = NO_OF_LINES * style.MENU_WIDTH_CHARS
                body_width -= ELLIPSIS_LENGTH
                if len(label) > body_width:
                    label = ' '.join(label[:body_width].split()[:-1]) + '...'
                label = textwrap.fill(label, width=style.MENU_WIDTH_CHARS)

            self._secondary_text = label
            self._secondary_label.set_text(label)
            self._secondary_label.set_visible(True)

    def get_secondary_text(self):
        return self._secondary_text

    secondary_text = GObject.Property(type=str, getter=get_secondary_text,
                                      setter=set_secondary_text)

    def _show_icon(self):
        self._label_alignment.set_margin_start(0)
        self._icon_box.set_visible(True)

    def _hide_icon(self):
        self._icon_box.set_visible(False)
        self._label_alignment.set_margin_start(style.DEFAULT_SPACING)

    def set_icon(self, icon):
        if icon is None:
            self._icon = None
            self._hide_icon()
        else:
            if self._icon:
                self._icon_box.remove(self._icon_box.get_children()[0])

            event_box = Gtk.Box()
            event_box.connect('button-release-event',
                              self.__icon_button_release_event_cb)
            self._icon_box.append(event_box)
            event_box.set_visible(True)

            self._icon = icon
            self._icon.props.pixel_size = style.STANDARD_ICON_SIZE
            event_box.append(self._icon)
            self._icon.set_visible(True)
            self._show_icon()

    def get_icon(self):
        return self._icon

    icon = GObject.Property(type=object, getter=get_icon, setter=set_icon)

    def __icon_button_release_event_cb(self, icon, event):
        self.emit('activate')

    def set_icon_visible(self, visible):
        self._icon_visible = visible

        if visible and self._icon is not None:
            self._show_icon()
        else:
            self._hide_icon()

    def get_icon_visible(self):
        return self._icon_visible

    icon_visible = GObject.Property(type=bool,
                                    default=True,
                                    getter=get_icon_visible,
                                    setter=set_icon_visible)

    def set_content(self, widget):
        assert self._widget is None \
            or isinstance(self._widget, _PaletteWindowWidget)

        if self._widget is None:
            self._widget = _PaletteWindowWidget(self)
            self._setup_widget()

            self._palette_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self._palette_box.append(self._primary_box)
            self._palette_box.append(self._secondary_box)

            self._widget.set_child(self._palette_box)
            self._palette_box.set_visible(True)
            height = style.GRID_CELL_SIZE - 2 * self._widget.get_border_width()
            self._primary_box.set_size_request(-1, height)

        if self._content.get_children():
            self._content.remove(self._content.get_children()[0])

        if widget is not None:
            widget.connect('button-release-event',
                           self.__widget_button_release_cb)
            self._content.append(widget)
            self._content.set_visible(True)
        else:
            self._content.set_visible(False)

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
        if self._widget is not None:
            self._full_request = self._widget.get_preferred_size()

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
            self._label_menuitem.set_visible(True)
            self._widget.append(self._label_menuitem)

            self._setup_widget()

        return self._widget

    menu = GObject.Property(type=object, getter=get_menu)

    def _invoker_right_click_cb(self, invoker):
        self.popup(immediate=True)


class PaletteActionBar(Gtk.Box):

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)

    def add_action(self, label, icon_name=None):
        button = Gtk.Button(label)

        if icon_name:
            icon = Icon(icon_name)
            button.set_child(icon)
            icon.set_visible(True)

        self.append(button)
        button.set_visible(True)

# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2008, Benjamin Berg <benjamin@sipsolutions.net>
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

import gettext
import gtk
import gobject
import struct
import logging

from sugar.graphics import style
from sugar.graphics.icon import Icon
from sugar.graphics.palette import Palette, ToolInvoker, WidgetInvoker


_ = lambda msg: gettext.dgettext('sugar-toolkit', msg)


def get_svg_color_string(color):
    return '#%.2X%.2X%.2X' % (color.red / 257, color.green / 257,
                              color.blue / 257)


class _ColorButton(gtk.Button):
    """This is a ColorButton for Sugar. It is similar to the gtk.ColorButton,
    but does not have any alpha support.
    Instead of a color selector dialog it will pop up a Sugar palette.

    As a preview an sugar.graphics.Icon is used. The fill color will be set to
    the current color, and the stroke color is set to the font color.
    """

    __gtype_name__ = 'SugarColorButton'
    __gsignals__ = {'color-set': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
        tuple())}

    def __init__(self, **kwargs):
        self._title = _('Choose a color')
        self._color = gtk.gdk.Color(0, 0, 0)
        self._has_palette = True
        self._has_invoker = True
        self._palette = None
        self._accept_drag = True

        self._preview = Icon(icon_name='color-preview',
                             icon_size=gtk.ICON_SIZE_BUTTON)

        gobject.GObject.__init__(self, **kwargs)

        if self._accept_drag:
            self.drag_dest_set(gtk.DEST_DEFAULT_MOTION |
                               gtk.DEST_DEFAULT_HIGHLIGHT |
                               gtk.DEST_DEFAULT_DROP,
                               [('application/x-color', 0, 0)],
                               gtk.gdk.ACTION_COPY)
        self.drag_source_set(gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK,
                             [('application/x-color', 0, 0)],
                             gtk.gdk.ACTION_COPY)
        self.connect('drag_data_received', self.__drag_data_received_cb)
        self.connect('drag_data_get', self.__drag_data_get_cb)

        self._preview.fill_color = get_svg_color_string(self._color)
        self._preview.stroke_color = \
            get_svg_color_string(self.style.fg[gtk.STATE_NORMAL])
        self.set_image(self._preview)

        if self._has_palette and self._has_invoker:
            self._invoker = WidgetInvoker(self)
            # FIXME: This is a hack.
            self._invoker.has_rectangle_gap = lambda: False
            self._invoker.palette = self._palette

    def create_palette(self):
        if self._has_palette:
            self._palette = _ColorPalette(color=self._color,
                                          primary_text=self._title)
            self._palette.connect('color-set', self.__palette_color_set_cb)
            self._palette.connect('notify::color', self.
                __palette_color_changed)

        return self._palette

    def __palette_color_set_cb(self, palette):
        self.emit('color-set')

    def __palette_color_changed(self, palette, pspec):
        self.color = self._palette.color

    def do_style_set(self, previous_style):
        self._preview.stroke_color = \
            get_svg_color_string(self.style.fg[gtk.STATE_NORMAL])

    def do_clicked(self):
        if self._palette:
            if not self._palette.is_up():
                self._palette.popup(immediate=True,
                                    state=self._palette.SECONDARY)
            else:
                self._palette.popdown(immediate=True)
            return True

    def set_color(self, color):
        assert isinstance(color, gtk.gdk.Color)

        if self._color.red == color.red and \
           self._color.green == color.green and \
           self._color.blue == color.blue:
            return

        self._color = gtk.gdk.Color(color.red, color.green, color.blue)
        self._preview.fill_color = get_svg_color_string(self._color)
        if self._palette:
            self._palette.props.color = self._color
        self.notify('color')

    def get_color(self):
        return self._color

    color = gobject.property(type=object, getter=get_color, setter=set_color)

    def set_icon_name(self, icon_name):
        self._preview.props.icon_name = icon_name

    def get_icon_name(self):
        return self._preview.props.icon_name

    icon_name = gobject.property(type=str,
                                 getter=get_icon_name, setter=set_icon_name)

    def set_icon_size(self, icon_size):
        self._preview.props.icon_size = icon_size

    def get_icon_size(self):
        return self._preview.props.icon_size

    icon_size = gobject.property(type=int,
                                 getter=get_icon_size, setter=set_icon_size)

    def set_title(self, title):
        self._title = title
        if self._palette:
            self._palette.primary_text = self._title

    def get_title(self):
        return self._title

    title = gobject.property(type=str, getter=get_title, setter=set_title)

    def _set_has_invoker(self, has_invoker):
        self._has_invoker = has_invoker

    def _get_has_invoker(self):
        return self._has_invoker

    has_invoker = gobject.property(type=bool, default=True,
                                   flags=gobject.PARAM_READWRITE |
                                         gobject.PARAM_CONSTRUCT_ONLY,
                                   getter=_get_has_invoker,
                                   setter=_set_has_invoker)

    def _set_has_palette(self, has_palette):
        self._has_palette = has_palette

    def _get_has_palette(self):
        return self._has_palette

    has_palette = gobject.property(type=bool, default=True,
                                   flags=gobject.PARAM_READWRITE |
                                         gobject.PARAM_CONSTRUCT_ONLY,
                                   getter=_get_has_palette,
                                   setter=_set_has_palette)

    def _set_accept_drag(self, accept_drag):
        self._accept_drag = accept_drag

    def _get_accept_drag(self):
        return self._accept_drag

    accept_drag = gobject.property(type=bool, default=True,
                                   flags=gobject.PARAM_READWRITE |
                                         gobject.PARAM_CONSTRUCT_ONLY,
                                   getter=_get_accept_drag,
                                   setter=_set_accept_drag)

    def __drag_begin_cb(self, widget, context):
        # Drag and Drop
        pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8,
                                style.SMALL_ICON_SIZE,
                                style.SMALL_ICON_SIZE)

        red = self._color.red / 257
        green = self._color.green / 257
        blue = self._color.blue / 257

        pixbuf.fill(red << 24 + green << 16 + blue << 8 + 0xff)

        context.set_icon_pixbuf(pixbuf)

    def __drag_data_get_cb(self, widget, context, selection_data, info, time):
        data = struct.pack('=HHHH', self._color.red, self._color.green,
                                    self._color.blue, 65535)
        selection_data.set(selection_data.target, 16, data)

    def __drag_data_received_cb(self, widget, context, x, y, selection_data, \
                               info, time):
        if len(selection_data.data) != 8:
            return

        dropped = selection_data.data
        red = struct.unpack_from('=H', dropped, 0)[0]
        green = struct.unpack_from('=H', dropped, 2)[0]
        blue = struct.unpack_from('=H', dropped, 4)[0]
        # dropped[6] and dropped[7] is alpha, but we ignore the alpha channel

        color = gtk.gdk.Color(red, green, blue)
        self.set_color(color)


class _ColorPalette(Palette):
    """This is a color picker palette. It will usually be used indirectly
    trough a sugar.graphics.ColorButton.
    """
    _RED = 0
    _GREEN = 1
    _BLUE = 2

    __gtype_name__ = 'SugarColorPalette'

    # The color-set signal is emitted when the user is finished selecting
    # a color.
    __gsignals__ = {'color-set': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
        tuple())}

    def __init__(self, **kwargs):
        self._color = gtk.gdk.Color(0, 0, 0)
        self._previous_color = self._color.copy()
        self._scales = None

        Palette.__init__(self, **kwargs)

        self.connect('popup', self.__popup_cb)
        self.connect('popdown', self.__popdown_cb)

        self._picker_hbox = gtk.HBox()
        self.set_content(self._picker_hbox)

        self._swatch_tray = gtk.Table()

        self._picker_hbox.pack_start(self._swatch_tray)
        self._picker_hbox.pack_start(gtk.VSeparator(),
                                     padding=style.DEFAULT_SPACING)

        self._chooser_table = gtk.Table(3, 2)
        self._chooser_table.set_col_spacing(0, style.DEFAULT_PADDING)

        self._scales = []
        self._scales.append(
            self._create_color_scale(_('Red'), self._RED, 0))
        self._scales.append(
            self._create_color_scale(_('Green'), self._GREEN, 1))
        self._scales.append(
            self._create_color_scale(_('Blue'), self._BLUE, 2))

        self._picker_hbox.add(self._chooser_table)

        self._picker_hbox.show_all()

        self._build_swatches()

    def _create_color_scale(self, text, color, row):
        label = gtk.Label(text)
        label.props.xalign = 1.0
        scale = gtk.HScale()
        scale.set_size_request(style.zoom(250), -1)
        scale.set_draw_value(False)
        scale.set_range(0, 1.0)
        scale.set_increments(0.1, 0.2)

        if color == self._RED:
            scale.set_value(self._color.red / 65535.0)
        elif color == self._GREEN:
            scale.set_value(self._color.green / 65535.0)
        elif color == self._BLUE:
            scale.set_value(self._color.blue / 65535.0)

        scale.connect('value-changed',
                      self.__scale_value_changed_cb,
                      color)
        self._chooser_table.attach(label, 0, 1, row, row + 1)
        self._chooser_table.attach(scale, 1, 2, row, row + 1)

        return scale

    def _build_swatches(self):
        for child in self._swatch_tray.get_children():
            child.destroy()

        # Use a hardcoded list of colors for now.
        colors = ['#ed2529', '#69bc47', '#3c54a3',
                  '#f57f25', '#0b6b3a', '#00a0c6',
                  '#f6eb1a', '#b93f94', '#5b4a9c',
                  '#000000', '#919496', '#ffffff']

        # We want 3 rows of colors.
        rows = 3
        i = 0
        self._swatch_tray.props.n_rows = rows
        self._swatch_tray.props.n_columns = (len(colors) + rows - 1) / rows
        for color in colors:
            button = _ColorButton(has_palette=False,
                                  color=gtk.gdk.color_parse(color),
                                  accept_drag=False,
                                  icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR)
            button.set_relief(gtk.RELIEF_NONE)
            self._swatch_tray.attach(button,
                                     i % rows, i % rows + 1,
                                     i / rows, i / rows + 1,
                                     yoptions=0, xoptions=0)
            button.connect('clicked', self.__swatch_button_clicked_cb)
            i += 1

        self._swatch_tray.show_all()

    def __popup_cb(self, palette):
        self._previous_color = self._color.copy()

    def __popdown_cb(self, palette):
        self.emit('color-set')

    def __scale_value_changed_cb(self, widget, color):
        new_color = self._color.copy()
        if color == self._RED:
            new_color.red = int(65535 * widget.get_value())
        elif color == self._GREEN:
            new_color.green = int(65535 * widget.get_value())
        elif color == self._BLUE:
            new_color.blue = int(65535 * widget.get_value())
        self.color = new_color

    def do_key_press_event(self, event):
        if event.keyval == gtk.keysyms.Escape:
            self.props.color = self._previous_color
            self.popdown(immediate=True)
            return True
        elif event.keyval == gtk.keysyms.Return:
            self.popdown(immediate=True)
            return True
        return False

    def __swatch_button_clicked_cb(self, button):
        self.props.color = button.get_color()

    def set_color(self, color):
        assert isinstance(color, gtk.gdk.Color)

        if self._color.red == color.red and \
           self._color.green == color.green and \
           self._color.blue == color.blue:
            return

        self._color = color.copy()

        if self._scales:
            self._scales[self._RED].set_value(self._color.red / 65535.0)
            self._scales[self._GREEN].set_value(self._color.green / 65535.0)
            self._scales[self._BLUE].set_value(self._color.blue / 65535.0)

        self.notify('color')

    def get_color(self):
        return self._color

    color = gobject.property(type=object, getter=get_color, setter=set_color)


def _add_accelerator(tool_button):
    if not tool_button.props.accelerator or not tool_button.get_toplevel() or \
            not tool_button.child:
        return

    # TODO: should we remove the accelerator from the prev top level?

    accel_group = tool_button.get_toplevel().get_data('sugar-accel-group')
    if not accel_group:
        logging.warning('No gtk.AccelGroup in the top level window.')
        return

    keyval, mask = gtk.accelerator_parse(tool_button.props.accelerator)
    # the accelerator needs to be set at the child, so the gtk.AccelLabel
    # in the palette can pick it up.
    tool_button.child.add_accelerator('clicked', accel_group, keyval, mask,
                                      gtk.ACCEL_LOCKED | gtk.ACCEL_VISIBLE)


def _hierarchy_changed_cb(tool_button, previous_toplevel):
    _add_accelerator(tool_button)


def setup_accelerator(tool_button):
    _add_accelerator(tool_button)
    tool_button.connect('hierarchy-changed', _hierarchy_changed_cb)


class ColorToolButton(gtk.ToolItem):
    # This not ideal. It would be better to subclass gtk.ToolButton, however
    # the python bindings do not seem to be powerfull enough for that.
    # (As we need to change a variable in the class structure.)

    __gtype_name__ = 'SugarColorToolButton'
    __gsignals__ = {'color-set': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
        tuple())}

    def __init__(self, icon_name='color-preview', **kwargs):
        self._accelerator = None
        self._tooltip = None
        self._palette_invoker = ToolInvoker()
        self._palette = None

        gobject.GObject.__init__(self, **kwargs)

        # The gtk.ToolButton has already added a normal button.
        # Replace it with a ColorButton
        color_button = _ColorButton(icon_name=icon_name, has_invoker=False)
        self.add(color_button)

        # The following is so that the behaviour on the toolbar is correct.
        color_button.set_relief(gtk.RELIEF_NONE)
        color_button.icon_size = gtk.ICON_SIZE_LARGE_TOOLBAR

        self._palette_invoker.attach_tool(self)

        # This widget just proxies the following properties to the colorbutton
        color_button.connect('notify::color', self.__notify_change)
        color_button.connect('notify::icon-name', self.__notify_change)
        color_button.connect('notify::icon-size', self.__notify_change)
        color_button.connect('notify::title', self.__notify_change)
        color_button.connect('color-set', self.__color_set_cb)
        color_button.connect('can-activate-accel',
                             self.__button_can_activate_accel_cb)

    def __button_can_activate_accel_cb(self, button, signal_id):
        # Accept activation via accelerators regardless of this widget's state
        return True

    def set_accelerator(self, accelerator):
        self._accelerator = accelerator
        setup_accelerator(self)

    def get_accelerator(self):
        return self._accelerator

    accelerator = gobject.property(type=str, setter=set_accelerator,
            getter=get_accelerator)

    def create_palette(self):
        self._palette = self.get_child().create_palette()
        return self._palette

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = gobject.property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker)

    def set_color(self, color):
        self.get_child().props.color = color

    def get_color(self):
        return self.get_child().props.color

    color = gobject.property(type=object, getter=get_color, setter=set_color)

    def set_icon_name(self, icon_name):
        self.get_child().props.icon_name = icon_name

    def get_icon_name(self):
        return self.get_child().props.icon_name

    icon_name = gobject.property(type=str,
                                 getter=get_icon_name, setter=set_icon_name)

    def set_icon_size(self, icon_size):
        self.get_child().props.icon_size = icon_size

    def get_icon_size(self):
        return self.get_child().props.icon_size

    icon_size = gobject.property(type=int,
                                 getter=get_icon_size, setter=set_icon_size)

    def set_title(self, title):
        self.get_child().props.title = title

    def get_title(self):
        return self.get_child().props.title

    title = gobject.property(type=str, getter=get_title, setter=set_title)

    def do_expose_event(self, event):
        child = self.get_child()
        allocation = self.get_allocation()
        if self._palette and self._palette.is_up():
            invoker = self._palette.props.invoker
            invoker.draw_rectangle(event, self._palette)
        elif child.state == gtk.STATE_PRELIGHT:
            child.style.paint_box(event.window, gtk.STATE_PRELIGHT,
                                  gtk.SHADOW_NONE, event.area,
                                  child, 'toolbutton-prelight',
                                  allocation.x, allocation.y,
                                  allocation.width, allocation.height)

        gtk.ToolButton.do_expose_event(self, event)

    def __notify_change(self, widget, pspec):
        self.notify(pspec.name)

    def __color_set_cb(self, widget):
        self.emit('color-set')

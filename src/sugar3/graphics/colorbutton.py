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
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk
from gi.repository import GObject
import struct
import logging

from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.palette import Palette, ToolInvoker, WidgetInvoker


def _(msg):
    return gettext.dgettext('sugar-toolkit-gtk3', msg)


if not hasattr(GObject.ParamFlags, 'READWRITE'):
    GObject.ParamFlags.READWRITE = GObject.ParamFlags.WRITABLE | \
        GObject.ParamFlags.READABLE


def get_svg_color_string(color):
    return '#%.2X%.2X%.2X' % (color.red // 257, color.green // 257,
                              color.blue // 257)


class _ColorButton(Gtk.Button):
    """
    This is a ColorButton for Sugar. It is similar to the Gtk.ColorButton,
    but does not have any alpha support.
    Instead of a color selector dialog it will pop up a Sugar palette.

    As a preview an sugar3.graphics.Icon is used. The fill color will be set to
    the current color, and the stroke color is set to the font color.
    """

    __gtype_name__ = 'SugarColorButton'
    __gsignals__ = {'color-set': (GObject.SignalFlags.RUN_FIRST, None,
                                  tuple())}

    def __init__(self, **kwargs):
        self._title = _('Choose a color')
        self._color = Gdk.Color(0, 0, 0)
        self._has_palette = True
        self._has_invoker = True
        self._palette = None
        self._accept_drag = True

        self._preview = Icon(icon_name='color-preview',
                             pixel_size=style.SMALL_ICON_SIZE)

        GObject.GObject.__init__(self, **kwargs)

        # FIXME Drag and drop is not working, SL #3796
        if self._accept_drag:
            self.drag_dest_set(Gtk.DestDefaults.MOTION |
                               Gtk.DestDefaults.HIGHLIGHT |
                               Gtk.DestDefaults.DROP,
                               [Gtk.TargetEntry.new(
                                'application/x-color', 0, 0)],
                               Gdk.DragAction.COPY)
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK |
                             Gdk.ModifierType.BUTTON3_MASK,
                             [Gtk.TargetEntry.new(
                                 'application/x-color', 0, 0)],
                             Gdk.DragAction.COPY)
        self.connect('drag-data-received', self.__drag_data_received_cb)
        self.connect('drag-data-get', self.__drag_data_get_cb)

        self._preview.fill_color = get_svg_color_string(self._color)
        self._preview.stroke_color = self._get_fg_style_color_str()
        self.set_image(self._preview)

        if self._has_palette and self._has_invoker:
            self._invoker = WidgetInvoker(self)
            # FIXME: This is a hack.
            self._invoker.has_rectangle_gap = lambda: False
            self._invoker.palette = self._palette

    def create_palette(self):
        '''
        Create a new palette with selected color and title.
        (Here the title is 'Choose a color' and the bgcolor
        is black.)
        '''
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
        self._preview.stroke_color = self._get_fg_style_color_str()

    def _get_fg_style_color_str(self):
        context = self.get_style_context()
        fg_color = context.get_color(Gtk.StateType.NORMAL)
        # the color components are stored as float values between 0.0 and 1.0
        return '#%.2X%.2X%.2X' % (int(fg_color.red * 255),
                                  int(fg_color.green * 255),
                                  int(fg_color.blue * 255))

    def set_color(self, color):
        assert isinstance(color, Gdk.Color)

        if self._color.red == color.red and \
           self._color.green == color.green and \
           self._color.blue == color.blue:
            return

        self._color = Gdk.Color(color.red, color.green, color.blue)
        self._preview.fill_color = get_svg_color_string(self._color)
        if self._palette:
            self._palette.props.color = self._color
        self.notify('color')

    def get_color(self):
        return self._color

    color = GObject.Property(type=object, getter=get_color, setter=set_color)

    def set_icon_name(self, icon_name):
        '''
        Sets the icon for the tool button from a named themed icon.
        If it is none then no icon will be shown.

        Args:
            icon_name(string): The name for a themed icon.
            It can be set as 'None' too.

        Example:
            set_icon_name('view-radial')
        '''
        self._preview.props.icon_name = icon_name

    def get_icon_name(self):
        '''
        The get_icon_name() method returns the value of the icon_name
        property that contains the name of a themed icon or None.
        '''
        return self._preview.props.icon_name

    icon_name = GObject.Property(type=str,
                                 getter=get_icon_name, setter=set_icon_name)

    def set_icon_size(self, pixel_size):
        self._preview.props.pixel_size = pixel_size

    def get_icon_size(self):
        return self._preview.props.pixel_size

    icon_size = GObject.Property(type=int,
                                 getter=get_icon_size, setter=set_icon_size)

    def set_title(self, title):
        self._title = title
        if self._palette:
            self._palette.primary_text = self._title

    def get_title(self):
        return self._title

    title = GObject.Property(type=str, getter=get_title, setter=set_title)

    def _set_has_invoker(self, has_invoker):
        self._has_invoker = has_invoker

    def _get_has_invoker(self):
        return self._has_invoker

    has_invoker = GObject.Property(type=bool, default=True,
                                   flags=GObject.ParamFlags.READWRITE |
                                   GObject.ParamFlags.CONSTRUCT_ONLY,
                                   getter=_get_has_invoker,
                                   setter=_set_has_invoker)

    def _set_has_palette(self, has_palette):
        self._has_palette = has_palette

    def _get_has_palette(self):
        return self._has_palette

    has_palette = GObject.Property(type=bool, default=True,
                                   flags=GObject.ParamFlags.READWRITE |
                                   GObject.ParamFlags.CONSTRUCT_ONLY,
                                   getter=_get_has_palette,
                                   setter=_set_has_palette)

    def _set_accept_drag(self, accept_drag):
        self._accept_drag = accept_drag

    def _get_accept_drag(self):
        return self._accept_drag

    accept_drag = GObject.Property(type=bool, default=True,
                                   flags=GObject.ParamFlags.READWRITE |
                                   GObject.ParamFlags.CONSTRUCT_ONLY,
                                   getter=_get_accept_drag,
                                   setter=_set_accept_drag)

    def __drag_begin_cb(self, widget, context):
        # Drag and Drop
        pixbuf = GdkPixbuf.Pixbuf(GdkPixbuf.Colorspace.RGB, True, 8,
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

    def __drag_data_received_cb(self, widget, context, x, y, selection_data,
                                info, time):
        if len(selection_data.data) != 8:
            return

        dropped = selection_data.data
        red = struct.unpack_from('=H', dropped, 0)[0]
        green = struct.unpack_from('=H', dropped, 2)[0]
        blue = struct.unpack_from('=H', dropped, 4)[0]
        # dropped[6] and dropped[7] is alpha, but we ignore the alpha channel

        color = Gdk.Color(red, green, blue)
        self.set_color(color)


class _ColorPalette(Palette):
    """This is a color picker palette. It will usually be used indirectly
    trough a sugar3.graphics.ColorButton.
    """
    _RED = 0
    _GREEN = 1
    _BLUE = 2

    __gtype_name__ = 'SugarColorPalette'

    # The color-set signal is emitted when the user is finished selecting
    # a color.
    __gsignals__ = {'color-set': (GObject.SignalFlags.RUN_FIRST, None,
                                  tuple())}

    def __init__(self, **kwargs):
        self._color = Gdk.Color(0, 0, 0)
        self._previous_color = self._color.copy()
        self._scales = None

        Palette.__init__(self, **kwargs)

        self.connect('popup', self.__popup_cb)
        self.connect('popdown', self.__popdown_cb)

        self._picker_hbox = Gtk.HBox()
        alignment = Gtk.Alignment()
        alignment.set_padding(0, 0, style.DEFAULT_SPACING,
                              style.DEFAULT_SPACING)
        alignment.add(self._picker_hbox)
        self.set_content(alignment)
        alignment.show()

        self._swatch_tray = Gtk.Table()

        self._picker_hbox.pack_start(self._swatch_tray, True, True, 0)
        self._picker_hbox.pack_start(Gtk.VSeparator(), True, True,
                                     padding=style.DEFAULT_SPACING)

        self._chooser_table = Gtk.Table(3, 2)
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
        label = Gtk.Label(label=text)
        label.props.xalign = 1.0
        scale = Gtk.HScale()
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
                                  color=Gdk.color_parse(color),
                                  accept_drag=False,
                                  icon_size=Gtk.IconSize.LARGE_TOOLBAR)
            button.set_relief(Gtk.ReliefStyle.NONE)
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
        if event.keyval == Gdk.KEY_Escape:
            self.props.color = self._previous_color
            self.popdown(immediate=True)
            return True
        elif event.keyval == Gdk.KEY_Return:
            self.popdown(immediate=True)
            return True
        return False

    def __swatch_button_clicked_cb(self, button):
        self.props.color = button.get_color()

    def set_color(self, color):
        assert isinstance(color, Gdk.Color)

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

    color = GObject.Property(type=object, getter=get_color, setter=set_color)


def _add_accelerator(tool_button):
    if not tool_button.props.accelerator or not tool_button.get_toplevel() or \
            not tool_button.get_child():
        return

    # TODO: should we remove the accelerator from the prev top level?

    if not hasattr(tool_button.get_toplevel(), 'sugar_accel_group'):
        logging.debug('No Gtk.AccelGroup in the top level window.')
        return

    accel_group = tool_button.get_toplevel().sugar_accel_group
    keyval, mask = Gtk.accelerator_parse(tool_button.props.accelerator)
    # the accelerator needs to be set at the child, so the Gtk.AccelLabel
    # in the palette can pick it up.
    tool_button.get_child(
    ).add_accelerator('clicked', accel_group, keyval, mask,
                      Gtk.AccelFlags.LOCKED | Gtk.AccelFlags.VISIBLE)


def _hierarchy_changed_cb(tool_button, previous_toplevel):
    _add_accelerator(tool_button)


def setup_accelerator(tool_button):
    _add_accelerator(tool_button)
    tool_button.connect('hierarchy-changed', _hierarchy_changed_cb)


class ColorToolButton(Gtk.ToolItem):
    # This not ideal. It would be better to subclass Gtk.ToolButton, however
    # the python bindings do not seem to be powerfull enough for that.
    # (As we need to change a variable in the class structure.)

    __gtype_name__ = 'SugarColorToolButton'
    __gsignals__ = {'color-set': (GObject.SignalFlags.RUN_FIRST, None,
                                  tuple())}

    def __init__(self, icon_name='color-preview', **kwargs):
        self._accelerator = None
        self._tooltip = None
        self._palette_invoker = ToolInvoker()
        self._palette = None

        GObject.GObject.__init__(self, **kwargs)

        # The Gtk.ToolButton has already added a normal button.
        # Replace it with a ColorButton
        color_button = _ColorButton(icon_name=icon_name, has_invoker=False)
        self.add(color_button)
        color_button.show()

        # The following is so that the behaviour on the toolbar is correct.
        color_button.set_relief(Gtk.ReliefStyle.NONE)
        color_button.icon_size = Gtk.IconSize.LARGE_TOOLBAR

        self._palette_invoker.attach_tool(self)
        self._palette_invoker.props.toggle_palette = True
        self._palette_invoker.props.lock_palette = True

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
        '''
        Sets keyboard shortcut that activates this button.

        Args:
            accelerator(string): accelerator to be set. Should be in
            form <modifier>Letter
            Find about format here :
            https://developer.gnome.org/gtk3/stable/gtk3-Keyboard-Accelerators.html#gtk-accelerator-parse

        Example:
            set_accelerator(self, 'accel')
        '''
        self._accelerator = accelerator
        setup_accelerator(self)

    def get_accelerator(self):
        '''
        Returns the above accelerator string.
        '''
        return self._accelerator

    accelerator = GObject.Property(type=str, setter=set_accelerator,
                                   getter=get_accelerator)

    def create_palette(self):
        '''
        The create_palette function is called when the palette needs to be
        invoked.  For example, when the user has right clicked the icon or
        the user has hovered over the icon for a long time.

        The create_palette will only be called once or zero times.  The palette
        returned will be stored and re-used if the user invokes the palette
        multiple times.

        Your create_palette implementation does not need to
        :any:`Gtk.Widget.show` the palette, as this will be done by the
        invoker.  However, you still need to show
        the menu items, etc that you place in the palette.

        Returns:

            sugar3.graphics.palette.Palette, or None to indicate that you
            do not want a palette shown

        The default implementation returns None, to indicate no palette should
        be shown.
        '''
        self._palette = self.get_child().create_palette()
        return self._palette

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = GObject.Property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker)

    def set_expanded(self, expanded):
        box = self.toolbar_box
        if not box:
            return

        if not expanded:
            self._palette_invoker.notify_popdown()
            return

        if box.expanded_button is not None:
            box.expanded_button.queue_draw()
            if box.expanded_button != self:
                box.expanded_button.set_expanded(False)
        box.expanded_button = self

    def get_toolbar_box(self):
        parent = self.get_parent()
        if not hasattr(parent, 'owner'):
            return None
        return parent.owner

    toolbar_box = property(get_toolbar_box)

    def set_color(self, color):
        '''
        Sets the color of the colorbutton
        '''
        self.get_child().props.color = color

    def get_color(self):
        '''
        Gets the above set color string.
        '''
        return self.get_child().props.color

    color = GObject.Property(type=object, getter=get_color, setter=set_color)

    def set_icon_name(self, icon_name):
        '''
        Sets the icon for the tool button from a named themed icon.
        If it is none then no icon will be shown.

        Args:
            icon_name(string): The name for a themed icon.
            It can be set as 'None' too.

        Example:
            set_icon_name('view-radial')
        '''
        self.get_child().props.icon_name = icon_name

    def get_icon_name(self):
        '''
        The get_icon_name() method returns the value of the icon_name
        property that contains the name of a themed icon or None.
        '''
        return self.get_child().props.icon_name

    icon_name = GObject.Property(type=str,
                                 getter=get_icon_name, setter=set_icon_name)

    def set_icon_size(self, icon_size):
        '''
        Sets the size of icons in the colorbutton.
        '''
        self.get_child().props.icon_size = icon_size

    def get_icon_size(self):
        '''
        Gets the size of icons in the colorbutton.
        '''
        return self.get_child().props.icon_size

    icon_size = GObject.Property(type=int,
                                 getter=get_icon_size, setter=set_icon_size)

    def set_title(self, title):
        '''
        The set_title() method sets the "title" property to the value of
        title. The "title" property contains the string that is used to
        set the colorbutton title.
        '''
        self.get_child().props.title = title

    def get_title(self):
        '''
        Return the above title string.
        '''
        return self.get_child().props.title

    title = GObject.Property(type=str, getter=get_title, setter=set_title)

    def do_draw(self, cr):
        if self._palette and self._palette.is_up():
            allocation = self.get_allocation()
            # draw a black background, has been done by the engine before
            cr.set_source_rgb(0, 0, 0)
            cr.rectangle(0, 0, allocation.width, allocation.height)
            cr.paint()

        Gtk.ToolItem.do_draw(self, cr)

        if self._palette and self._palette.is_up():
            invoker = self._palette.props.invoker
            invoker.draw_rectangle(cr, self._palette)

        return False

    def __notify_change(self, widget, pspec):
        self.notify(pspec.name)

    def __color_set_cb(self, widget):
        self.emit('color-set')

# Copyright (C) 2009 One Laptop Per Child
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
import os

from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GConf

from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.icon import get_icon_file_name
from sugar3.graphics.toolbutton import ToolButton

from sugar3.bundle.activitybundle import ActivityBundle


_ = lambda msg: gettext.dgettext('sugar-toolkit', msg)


def _get_icon_name(metadata):
    file_name = None

    mime_type = metadata.get('mime_type', '')
    if not file_name and mime_type:
        icons = Gio.content_type_get_icon(mime_type)
        for icon_name in icons.props.names:
            file_name = get_icon_file_name(icon_name)
            if file_name is not None:
                break

    if file_name is None or not os.path.exists(file_name):
        file_name = get_icon_file_name('application-octet-stream')

    return file_name


class NamingToolbar(Gtk.Toolbar):
    """ Toolbar of the naming alert
    """

    __gtype_name__ = 'SugarNamingToolbar'

    __gsignals__ = {
        'keep-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        Gtk.Toolbar.__init__(self)

        client = GConf.Client.get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
        icon = Icon()
        icon.set_from_icon_name('activity-journal',
                                Gtk.IconSize.LARGE_TOOLBAR)
        icon.props.xo_color = color
        self._add_widget(icon)

        self._add_separator()

        self._title = Gtk.Label(label=_('Name this entry'))
        self._add_widget(self._title)

        self._add_separator(True)

        self._keep_button = ToolButton('dialog-ok', tooltip=_('Keep'))
        self._keep_button.props.accelerator = 'Return'
        self._keep_button.connect('clicked', self.__keep_button_clicked_cb)
        self.insert(self._keep_button, -1)
        self._keep_button.show()

    def _add_separator(self, expand=False):
        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        if expand:
            separator.set_expand(True)
        else:
            separator.set_size_request(style.DEFAULT_SPACING, -1)
        self.insert(separator, -1)
        separator.show()

    def _add_widget(self, widget, expand=False):
        tool_item = Gtk.ToolItem()
        tool_item.set_expand(expand)

        tool_item.add(widget)
        widget.show()

        self.insert(tool_item, -1)
        tool_item.show()

    def __keep_button_clicked_cb(self, widget, data=None):
        self.emit('keep-clicked')


class FavoriteIcon(Gtk.ToggleButton):

    def __init__(self):
        GObject.GObject.__init__(self)
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_focus_on_click(False)

        self._icon = Icon(icon_name='emblem-favorite',
                          pixel_size=style.SMALL_ICON_SIZE)
        self.set_image(self._icon)

        self.connect('toggled', self.__toggled_cb)
        self.connect('leave-notify-event', self.__leave_notify_event_cb)
        self.connect('enter-notify-event', self.__enter_notify_event_cb)

    def __toggled_cb(self, widget):
        if self.get_active():
            client = GConf.Client.get_default()
            color = XoColor(client.get_string('/desktop/sugar/user/color'))
            self._icon.props.xo_color = color
        else:
            self._icon.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
            self._icon.props.fill_color = style.COLOR_WHITE.get_svg()

    def __enter_notify_event_cb(self, icon, event):
        if not self.get_active():
            self._icon.props.fill_color = style.COLOR_BUTTON_GREY.get_svg()

    def __leave_notify_event_cb(self, icon, event):
        if not self.get_active():
            self._icon.props.fill_color = style.COLOR_TRANSPARENT.get_svg()


class NamingAlert(Gtk.Window):

    __gtype_name__ = 'SugarNamingAlert'

    def __init__(self, activity, bundle_path):
        GObject.GObject.__init__(self)

        self._bundle_path = bundle_path
        self._favorite_icon = None
        self._title = None
        self._description = None
        self._tags = None

        accel_group = Gtk.AccelGroup()
        self.set_data('sugar-accel-group', accel_group)
        self.add_accel_group(accel_group)

        self.set_border_width(style.LINE_WIDTH)
        offset = style.GRID_CELL_SIZE
        width = Gdk.Screen.width() - offset * 2
        height = Gdk.Screen.height() - offset * 2
        self.set_size_request(width, height)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)
        self.connect('realize', self.__realize_cb)

        self._activity = activity

        vbox = Gtk.VBox()
        self.add(vbox)
        vbox.show()

        toolbar = NamingToolbar()
        toolbar.connect('keep-clicked', self.__keep_cb)
        vbox.pack_start(toolbar, False, False, 0)
        toolbar.show()

        body = self._create_body()
        vbox.pack_start(body, True, True, 0)
        body.show()

        self._title.grab_focus()

    def _create_body(self):
        body = Gtk.VBox(spacing=style.DEFAULT_SPACING)
        body.set_border_width(style.DEFAULT_SPACING * 3)
        header = self._create_header()
        body.pack_start(header, False, False, style.DEFAULT_PADDING)

        body.pack_start(self._create_separator(style.DEFAULT_SPACING), False, False, 0)

        body.pack_start(self._create_label(_('Description:')), False, False, 0)

        description = self._activity.metadata.get('description', '')
        description_box, self._description = self._create_text_view(description)
        body.pack_start(description_box, True, True, 0)

        body.pack_start(self._create_separator(style.DEFAULT_PADDING), False, False, 0)


        body.pack_start(self._create_label(_('Tags:')), False, False, 0)

        tags = self._activity.metadata.get('tags', '')
        tags_box, self._tags = self._create_text_view(tags)
        body.pack_start(tags_box, True, True, 0)

        body.show_all()
        return body

    def _create_label(self, text):
        text = Gtk.Label(label=text)
        text.set_alignment(0, 0.5)
        text.modify_fg(Gtk.StateType.NORMAL,
                       style.COLOR_BUTTON_GREY.get_gdk_color())
        return text

    def _create_separator(self, height):
        separator = Gtk.HSeparator()
        separator.modify_bg(Gtk.StateType.NORMAL, style.COLOR_WHITE.get_gdk_color())
        separator.set_size_request(-1, height)
        return separator

    def _create_header(self):
        header = Gtk.HBox(spacing=style.DEFAULT_SPACING)

        self._favorite_icon = FavoriteIcon()
        header.pack_start(self._favorite_icon, False, True, 0)

        entry_icon = self._create_entry_icon()
        header.pack_start(entry_icon, False, True, 0)

        self._title = self._create_title()
        header.pack_start(self._title, True, True, 0)

        return header

    def _create_entry_icon(self):
        bundle_id = self._activity.metadata.get('activity', '')
        if not bundle_id:
            bundle_id = self._activity.metadata.get('bundle_id', '')

        if bundle_id == '':
            file_name = _get_icon_name(self._activity.metadata)
        else:
            activity_bundle = ActivityBundle(self._bundle_path)
            file_name = activity_bundle.get_icon()
        entry_icon = Icon(file=file_name, icon_size=Gtk.IconSize.LARGE_TOOLBAR)
        if self._activity.metadata.get('icon-color'):
            entry_icon.props.xo_color = XoColor( \
                self._activity.metadata['icon-color'])
        return entry_icon

    def _create_title(self):
        title = Gtk.Entry()
        title.set_text(self._activity.metadata.get('title', _('Untitled')))
        return title

    def _create_text_view(self, text):
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_border_width(style.LINE_WIDTH)
        scrolled_window.set_shadow_type(Gtk.ShadowType.IN)

        text_view = Gtk.TextView()
        text_view.set_left_margin(style.DEFAULT_PADDING)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_accepts_tab(False)
        text_view.get_buffer().set_text(text)
        scrolled_window.add(text_view)

        return scrolled_window, text_view

    def __realize_cb(self, widget):
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.get_window().set_accept_focus(True)

    def __keep_cb(self, widget):
        if self._favorite_icon.get_active():
            self._activity.metadata['keep'] = 1
        else:
            self._activity.metadata['keep'] = 0

        self._activity.metadata['title'] = self._title.get_text()

        text_buffer = self._tags.get_buffer()
        start, end = text_buffer.get_bounds()
        new_tags = text_buffer.get_text(start, end, False)
        self._activity.metadata['tags'] = new_tags

        text_buffer = self._description.get_buffer()
        start, end = text_buffer.get_bounds()
        new_description = text_buffer.get_text(start, end, False)
        self._activity.metadata['description'] = new_description

        self._activity.metadata['title_set_by_user'] = '1'
        self._activity.close()
        self.destroy()

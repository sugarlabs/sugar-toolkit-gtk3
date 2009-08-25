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

import gio
import gtk
import gobject
import hippo
import gconf

from sugar.graphics import style
from sugar.graphics.icon import Icon
from sugar.graphics.xocolor import XoColor
from sugar.graphics.icon import CanvasIcon
from sugar.graphics.icon import get_icon_file_name
from sugar.graphics.entry import CanvasEntry
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.canvastextview import CanvasTextView

from sugar.bundle.activitybundle import ActivityBundle


_ = lambda msg: gettext.dgettext('sugar-toolkit', msg)


def _get_icon_name(metadata):
    file_name = None

    mime_type = metadata.get('mime_type', '')
    if not file_name and mime_type:
        icons = gio.content_type_get_icon(mime_type)
        for icon_name in icons.props.names:
            file_name = get_icon_file_name(icon_name)
            if file_name is not None:
                break

    if file_name is None or not os.path.exists(file_name):
        file_name = get_icon_file_name('application-octet-stream')

    return file_name


class NamingToolbar(gtk.Toolbar):
    """ Toolbar of the naming alert
    """

    __gtype_name__ = 'SugarNamingToolbar'

    __gsignals__ = {
        'keep-clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
    }

    def __init__(self):
        gtk.Toolbar.__init__(self)

        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
        icon = Icon()
        icon.set_from_icon_name('activity-journal',
                                gtk.ICON_SIZE_LARGE_TOOLBAR)
        icon.props.xo_color = color
        self._add_widget(icon)

        self._add_separator()

        self._title = gtk.Label(_('Name this entry'))
        self._add_widget(self._title)

        self._add_separator(True)

        self._keep_button = ToolButton('dialog-ok', tooltip=_('Keep'))
        self._keep_button.props.accelerator = 'Return'
        self._keep_button.connect('clicked', self.__keep_button_clicked_cb)
        self.insert(self._keep_button, -1)
        self._keep_button.show()

    def _add_separator(self, expand=False):
        separator = gtk.SeparatorToolItem()
        separator.props.draw = False
        if expand:
            separator.set_expand(True)
        else:
            separator.set_size_request(style.DEFAULT_SPACING, -1)
        self.insert(separator, -1)
        separator.show()

    def _add_widget(self, widget, expand=False):
        tool_item = gtk.ToolItem()
        tool_item.set_expand(expand)

        tool_item.add(widget)
        widget.show()

        self.insert(tool_item, -1)
        tool_item.show()

    def __keep_button_clicked_cb(self, widget, data=None):
        self.emit('keep-clicked')


class FavoriteIcon(CanvasIcon):

    def __init__(self, favorite):
        CanvasIcon.__init__(self, icon_name='emblem-favorite',
                            box_width=style.GRID_CELL_SIZE * 3 / 5,
                            size=style.SMALL_ICON_SIZE)
        self._favorite = None
        self.set_favorite(favorite)
        self.connect('button-release-event', self.__release_event_cb)
        self.connect('motion-notify-event', self.__motion_notify_event_cb)

    def set_favorite(self, favorite):
        if favorite == self._favorite:
            return

        self._favorite = favorite
        if favorite:
            client = gconf.client_get_default()
            color = XoColor(client.get_string('/desktop/sugar/user/color'))
            self.props.xo_color = color
        else:
            self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
            self.props.fill_color = style.COLOR_WHITE.get_svg()

    def get_favorite(self):
        return self._favorite

    favorite = gobject.property(
        type=bool, default=False, getter=get_favorite, setter=set_favorite)

    def __release_event_cb(self, icon, event):
        self.props.favorite = not self.props.favorite

    def __motion_notify_event_cb(self, icon, event):
        if not self._favorite:
            if event.detail == hippo.MOTION_DETAIL_ENTER:
                icon.props.fill_color = style.COLOR_BUTTON_GREY.get_svg()
            elif event.detail == hippo.MOTION_DETAIL_LEAVE:
                icon.props.fill_color = style.COLOR_TRANSPARENT.get_svg()


class NamingAlert(gtk.Window):

    __gtype_name__ = 'SugarNamingAlert'

    def __init__(self, activity, bundle_path):
        gtk.Window.__init__(self)

        self._bundle_path = bundle_path
        self._favorite_icon = None
        self._title = None
        self._description = None
        self._tags = None

        accel_group = gtk.AccelGroup()
        self.set_data('sugar-accel-group', accel_group)
        self.add_accel_group(accel_group)

        self.set_border_width(style.LINE_WIDTH)
        offset = style.GRID_CELL_SIZE
        width = gtk.gdk.screen_width() - offset * 2
        height = gtk.gdk.screen_height() - offset * 2
        self.set_size_request(width, height)
        self.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)
        self.connect('realize', self.__realize_cb)

        self._activity = activity

        vbox = gtk.VBox()
        self.add(vbox)
        vbox.show()

        toolbar = NamingToolbar()
        toolbar.connect('keep-clicked', self.__keep_cb)
        vbox.pack_start(toolbar, False)
        toolbar.show()

        canvas = hippo.Canvas()
        self._root = hippo.CanvasBox()
        self._root.props.background_color = style.COLOR_WHITE.get_int()
        canvas.set_root(self._root)
        vbox.pack_start(canvas)
        canvas.show()

        body = self._create_body()
        self._root.append(body, hippo.PACK_EXPAND)

        widget = self._title.get_property('widget')
        widget.grab_focus()

    def _create_body(self):
        body = hippo.CanvasBox()
        body.props.orientation = hippo.ORIENTATION_VERTICAL
        body.props.background_color = style.COLOR_WHITE.get_int()
        body.props.padding_top = style.DEFAULT_SPACING * 3

        header = hippo.CanvasBox(orientation=hippo.ORIENTATION_HORIZONTAL,
                                 padding=style.DEFAULT_PADDING,
                                 padding_right=style.GRID_CELL_SIZE,
                                 spacing=style.DEFAULT_SPACING)
        body.append(header)

        descriptions = hippo.CanvasBox(
            orientation=hippo.ORIENTATION_HORIZONTAL,
            spacing=style.DEFAULT_SPACING * 3,
            padding_left=style.GRID_CELL_SIZE,
            padding_right=style.GRID_CELL_SIZE,
            padding_top=style.DEFAULT_SPACING * 3)

        body.append(descriptions, hippo.PACK_EXPAND)

        first_column = hippo.CanvasBox(orientation=hippo.ORIENTATION_VERTICAL,
                                       spacing=style.DEFAULT_SPACING)
        descriptions.append(first_column)

        second_column = hippo.CanvasBox(orientation=hippo.ORIENTATION_VERTICAL,
                                       spacing=style.DEFAULT_SPACING)
        descriptions.append(second_column, hippo.PACK_EXPAND)

        self._favorite_icon = self._create_favorite_icon()
        header.append(self._favorite_icon)

        entry_icon = self._create_entry_icon()
        header.append(entry_icon)

        self._title = self._create_title()
        header.append(self._title, hippo.PACK_EXPAND)

        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
            header.reverse()

        description_box, self._description = self._create_description()
        second_column.append(description_box)

        tags_box, self._tags = self._create_tags()
        second_column.append(tags_box)

        return body

    def _create_favorite_icon(self):
        favorite_icon = FavoriteIcon(False)
        return favorite_icon

    def _create_entry_icon(self):
        bundle_id = self._activity.metadata.get('activity', '')
        if not bundle_id:
            bundle_id = self._activity.metadata.get('bundle_id', '')

        if bundle_id == '':
            file_name = _get_icon_name(self._activity.metadata)
        else:
            activity_bundle = ActivityBundle(self._bundle_path)
            file_name = activity_bundle.get_icon()
        entry_icon = CanvasIcon(file_name=file_name)
        if self._activity.metadata.has_key('icon-color') and \
                self._activity.metadata['icon-color']:
            entry_icon.props.xo_color = XoColor( \
                self._activity.metadata['icon-color'])
        return entry_icon

    def _create_title(self):
        title = CanvasEntry()
        title.set_background(style.COLOR_WHITE.get_html())
        title.props.text = self._activity.metadata.get('title', _('Untitled'))
        return title

    def _create_description(self):
        vbox = hippo.CanvasBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        text = hippo.CanvasText(text=_('Description:'),
                                font_desc=style.FONT_NORMAL.get_pango_desc())
        text.props.color = style.COLOR_BUTTON_GREY.get_int()

        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
            text.props.xalign = hippo.ALIGNMENT_END
        else:
            text.props.xalign = hippo.ALIGNMENT_START

        vbox.append(text)

        description = self._activity.metadata.get('description', '')
        text_view = CanvasTextView(description,
                                   box_height=style.GRID_CELL_SIZE * 2)
        vbox.append(text_view, hippo.PACK_EXPAND)

        text_view.text_view_widget.props.accepts_tab = False

        return vbox, text_view

    def _create_tags(self):
        vbox = hippo.CanvasBox()
        vbox.props.spacing = style.DEFAULT_SPACING

        text = hippo.CanvasText(text=_('Tags:'),
                                font_desc=style.FONT_NORMAL.get_pango_desc())
        text.props.color = style.COLOR_BUTTON_GREY.get_int()

        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_RTL:
            text.props.xalign = hippo.ALIGNMENT_END
        else:
            text.props.xalign = hippo.ALIGNMENT_START

        vbox.append(text)

        tags = self._activity.metadata.get('tags', '')
        text_view = CanvasTextView(tags, box_height=style.GRID_CELL_SIZE * 2)
        vbox.append(text_view, hippo.PACK_EXPAND)

        text_view.text_view_widget.props.accepts_tab = False

        return vbox, text_view

    def __realize_cb(self, widget):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.window.set_accept_focus(True)

    def __keep_cb(self, widget):
        is_favorite = self._favorite_icon.get_favorite()
        if is_favorite:
            self._activity.metadata['keep'] = 1
        else:
            self._activity.metadata['keep'] = 0

        self._activity.metadata['title'] = self._title.props.text

        new_tags = self._tags.text_view_widget.props.buffer.props.text
        self._activity.metadata['tags'] = new_tags

        new_description = \
                self._description.text_view_widget.props.buffer.props.text
        self._activity.metadata['description'] = new_description

        self._activity.metadata['title_set_by_user'] = '1'
        self._activity.close()
        self.destroy()

# Copyright (C) 2009, Aleksey Lim, Simon Schampijer
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

import gtk
import gobject
import gettext
import gconf

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toolbarbox import ToolbarButton
from sugar.graphics.radiopalette import RadioPalette, RadioMenuButton
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.toolbox import Toolbox
from sugar.graphics.xocolor import XoColor
from sugar.graphics.icon import Icon
from sugar.bundle.activitybundle import ActivityBundle


_ = lambda msg: gettext.dgettext('sugar-toolkit', msg)


def _create_activity_icon(metadata):
    if metadata.get('icon-color', ''):
        color = XoColor(metadata['icon-color'])
    else:
        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))

    from sugar.activity.activity import get_bundle_path
    bundle = ActivityBundle(get_bundle_path())
    icon = Icon(file=bundle.get_icon(), xo_color=color)

    return icon


class ActivityButton(ToolButton):

    def __init__(self, activity, **kwargs):
        ToolButton.__init__(self, **kwargs)

        icon = _create_activity_icon(activity.metadata)
        self.set_icon_widget(icon)
        icon.show()

        self.props.tooltip = activity.metadata['title']
        activity.metadata.connect('updated', self.__jobject_updated_cb)

    def __jobject_updated_cb(self, jobject):
        self.props.tooltip = jobject['title']


class ActivityToolbarButton(ToolbarButton):

    def __init__(self, activity, **kwargs):
        toolbar = ActivityToolbar(activity, orientation_left=True)
        toolbar.stop.hide()

        ToolbarButton.__init__(self, page=toolbar, **kwargs)

        icon = _create_activity_icon(activity.metadata)
        self.set_icon_widget(icon)
        icon.show()


class StopButton(ToolButton):

    def __init__(self, activity, **kwargs):
        ToolButton.__init__(self, 'activity-stop', **kwargs)
        self.props.tooltip = _('Stop')
        self.props.accelerator = '<Ctrl>Q'
        self.connect('clicked', self.__stop_button_clicked_cb, activity)

    def __stop_button_clicked_cb(self, button, activity):
        activity.close()


class UndoButton(ToolButton):

    def __init__(self, **kwargs):
        ToolButton.__init__(self, 'edit-undo', **kwargs)
        self.props.tooltip = _('Undo')
        self.props.accelerator = '<Ctrl>Z'


class RedoButton(ToolButton):

    def __init__(self, **kwargs):
        ToolButton.__init__(self, 'edit-redo', **kwargs)
        self.props.tooltip = _('Redo')


class CopyButton(ToolButton):

    def __init__(self, **kwargs):
        ToolButton.__init__(self, 'edit-copy', **kwargs)
        self.props.tooltip = _('Copy')
        self.props.accelerator = '<Ctrl>C'


class PasteButton(ToolButton):

    def __init__(self, **kwargs):
        ToolButton.__init__(self, 'edit-paste', **kwargs)
        self.props.tooltip = _('Paste')
        self.props.accelerator = '<Ctrl>V'


class ShareButton(RadioMenuButton):

    def __init__(self, activity, **kwargs):
        palette = RadioPalette()

        self.private = RadioToolButton(
                icon_name='zoom-home')
        palette.append(self.private, _('Private'))

        self.neighborhood = RadioToolButton(
                icon_name='zoom-neighborhood',
                group=self.private)
        self._neighborhood_handle = self.neighborhood.connect(
                'clicked', self.__neighborhood_clicked_cb, activity)
        palette.append(self.neighborhood, _('My Neighborhood'))

        activity.connect('shared', self.__update_share_cb)
        activity.connect('joined', self.__update_share_cb)

        RadioMenuButton.__init__(self, **kwargs)
        self.props.palette = palette
        if activity.max_participants == 1:
            self.props.sensitive = False

    def __neighborhood_clicked_cb(self, button, activity):
        activity.share()

    def __update_share_cb(self, activity):
        self.neighborhood.handler_block(self._neighborhood_handle)
        try:
            if activity.shared_activity is not None and \
                    not activity.shared_activity.props.private:
                self.private.props.sensitive = False
                self.neighborhood.props.sensitive = False
                self.neighborhood.props.active = True
            else:
                self.private.props.sensitive = True
                self.neighborhood.props.sensitive = True
                self.private.props.active = True
        finally:
            self.neighborhood.handler_unblock(self._neighborhood_handle)


class KeepButton(ToolButton):

    def __init__(self, activity, **kwargs):
        ToolButton.__init__(self, **kwargs)
        self.props.tooltip = _('Keep')
        self.props.accelerator = '<Ctrl>S'

        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
        keep_icon = Icon(icon_name='document-save', xo_color=color)
        keep_icon.show()

        self.set_icon_widget(keep_icon)
        self.connect('clicked', self.__keep_button_clicked_cb, activity)

    def __keep_button_clicked_cb(self, button, activity):
        activity.copy()


class TitleEntry(gtk.ToolItem):

    def __init__(self, activity, **kwargs):
        gtk.ToolItem.__init__(self)
        self.set_expand(False)
        self._update_title_sid = None

        self.entry = gtk.Entry(**kwargs)
        self.entry.set_size_request(int(gtk.gdk.screen_width() / 3), -1)
        self.entry.set_text(activity.metadata['title'])
        self.entry.connect('changed', self.__title_changed_cb, activity)
        self.entry.show()
        self.add(self.entry)

        activity.metadata.connect('updated', self.__jobject_updated_cb)

    def modify_bg(self, state, color):
        gtk.ToolItem.modify_bg(self, state, color)
        self.entry.modify_bg(state, color)

    def __jobject_updated_cb(self, jobject):
        self.entry.set_text(jobject['title'])

    def __title_changed_cb(self, entry, activity):
        if self._update_title_sid is not None:
            gobject.source_remove(self._update_title_sid)
        self._update_title_sid = gobject.timeout_add_seconds(
                1, self.__update_title_cb, activity)

    def __update_title_cb(self, activity):
        title = self.entry.get_text()

        activity.metadata['title'] = title
        activity.metadata['title_set_by_user'] = '1'
        activity.save()

        shared_activity = activity.get_shared_activity()
        if shared_activity is not None:
            shared_activity.props.name = title

        self._update_title_sid = None
        return False


class ActivityToolbar(gtk.Toolbar):
    """The Activity toolbar with the Journal entry title, sharing,
       Keep and Stop buttons

    All activities should have this toolbar. It is easiest to add it to your
    Activity by using the ActivityToolbox.
    """

    def __init__(self, activity, orientation_left=False):
        gtk.Toolbar.__init__(self)

        self._activity = activity

        if activity.metadata:
            title_button = TitleEntry(activity)
            title_button.show()
            self.insert(title_button, -1)
            self.title = title_button.entry

        if orientation_left == False:
            separator = gtk.SeparatorToolItem()
            separator.props.draw = False
            separator.set_expand(True)
            self.insert(separator, -1)
            separator.show()

        self.share = ShareButton(activity)
        self.share.show()
        self.insert(self.share, -1)

        self.keep = KeepButton(activity)
        self.insert(self.keep, -1)
        self.keep.show()

        self.stop = StopButton(activity)
        self.insert(self.stop, -1)
        self.stop.show()


class EditToolbar(gtk.Toolbar):
    """Provides the standard edit toolbar for Activities.

    Members:
        undo  -- the undo button
        redo  -- the redo button
        copy  -- the copy button
        paste -- the paste button
        separator -- A separator between undo/redo and copy/paste

    This class only provides the 'edit' buttons in a standard layout,
    your activity will need to either hide buttons which make no sense for your
    Activity, or you need to connect the button events to your own callbacks:

        ## Example from Read.activity:
        # Create the edit toolbar:
        self._edit_toolbar = EditToolbar(self._view)
        # Hide undo and redo, they're not needed
        self._edit_toolbar.undo.props.visible = False
        self._edit_toolbar.redo.props.visible = False
        # Hide the separator too:
        self._edit_toolbar.separator.props.visible = False

        # As long as nothing is selected, copy needs to be insensitive:
        self._edit_toolbar.copy.set_sensitive(False)
        # When the user clicks the button, call _edit_toolbar_copy_cb()
        self._edit_toolbar.copy.connect('clicked', self._edit_toolbar_copy_cb)

        # Add the edit toolbar:
        toolbox.add_toolbar(_('Edit'), self._edit_toolbar)
        # And make it visible:
        self._edit_toolbar.show()
    """

    def __init__(self):
        gtk.Toolbar.__init__(self)

        self.undo = UndoButton()
        self.insert(self.undo, -1)
        self.undo.show()

        self.redo = RedoButton()
        self.insert(self.redo, -1)
        self.redo.show()

        self.separator = gtk.SeparatorToolItem()
        self.separator.set_draw(True)
        self.insert(self.separator, -1)
        self.separator.show()

        self.copy = CopyButton()
        self.insert(self.copy, -1)
        self.copy.show()

        self.paste = PasteButton()
        self.insert(self.paste, -1)
        self.paste.show()


class ActivityToolbox(Toolbox):
    """Creates the Toolbox for the Activity

    By default, the toolbox contains only the ActivityToolbar. After creating
    the toolbox, you can add your activity specific toolbars, for example the
    EditToolbar.

    To add the ActivityToolbox to your Activity in MyActivity.__init__() do:

        # Create the Toolbar with the ActivityToolbar:
        toolbox = activity.ActivityToolbox(self)
        ... your code, inserting all other toolbars you need, like EditToolbar

        # Add the toolbox to the activity frame:
        self.set_toolbar_box(toolbox)
        # And make it visible:
        toolbox.show()
    """

    def __init__(self, activity):
        Toolbox.__init__(self)

        self._activity_toolbar = ActivityToolbar(activity)
        self.add_toolbar(_('Activity'), self._activity_toolbar)
        self._activity_toolbar.show()

    def get_activity_toolbar(self):
        return self._activity_toolbar

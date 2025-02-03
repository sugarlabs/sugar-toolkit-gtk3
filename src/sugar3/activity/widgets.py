# Copyright (C) 2009, Aleksey Lim, Simon Schampijer
# Copyright (C) 2012, Walter Bender
# Copyright (C) 2012, One Laptop Per Child
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

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GObject
import gettext

from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toolbarbox import ToolbarButton
from sugar3.graphics.radiopalette import RadioPalette, RadioMenuButton
from sugar3.graphics.radiotoolbutton import RadioToolButton
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.icon import Icon
from sugar3.bundle.activitybundle import get_bundle_instance
from sugar3.graphics import style
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3 import profile


def _(msg):
    return gettext.dgettext('sugar-toolkit-gtk3', msg)


def _create_activity_icon(metadata):
    if metadata is not None and metadata.get('icon-color'):
        color = XoColor(metadata['icon-color'])
    else:
        color = profile.get_color()

    from sugar3.activity.activity import get_bundle_path
    bundle = get_bundle_instance(get_bundle_path())
    icon = Icon(file=bundle.get_icon(), xo_color=color)

    return icon


class ActivityButton(ToolButton):

    def __init__(self, activity, **kwargs):
        ToolButton.__init__(self, **kwargs)

        icon = _create_activity_icon(activity.metadata)
        self.set_child(icon)
        icon.set_visible(True)

        self.props.hide_tooltip_on_click = False
        self.palette_invoker.props.toggle_palette = True
        self.props.tooltip_text = activity.metadata['title']
        activity.metadata.connect('updated', self.__jobject_updated_cb)

    def __jobject_updated_cb(self, jobject):
        self.props.tooltip_text = jobject['title']


class ActivityToolbarButton(ToolbarButton):

    def __init__(self, activity, **kwargs):
        toolbar = ActivityToolbar(activity, orientation_left=True)
        toolbar.connect('enter-key-press', lambda widget: self.emit('clicked'))

        ToolbarButton.__init__(self, page=toolbar, **kwargs)

        icon = _create_activity_icon(activity.metadata)
        self.set_child(icon)
        icon.set_visible(True)


class StopButton(ToolButton):

    def __init__(self, activity, **kwargs):
        ToolButton.__init__(self, 'activity-stop', **kwargs)
        self.props.tooltip_text = _('Stop')
        self.props.accelerator = '<Ctrl>Q'
        self.connect('clicked', self.__stop_button_clicked_cb, activity)
        activity.add_stop_button(self)

    def __stop_button_clicked_cb(self, button, activity):
        activity.close()
    
    def get_toplevel(self):
        return self.get_ancestor(Gtk.Window)

class UndoButton(ToolButton):

    def __init__(self, **kwargs):
        ToolButton.__init__(self, 'edit-undo', **kwargs)
        self.props.tooltip_text = _('Undo')
        self.props.accelerator = '<Ctrl>Z'


class RedoButton(ToolButton):

    def __init__(self, **kwargs):
        ToolButton.__init__(self, 'edit-redo', **kwargs)
        self.props.tooltip_text = _('Redo')
        self.props.accelerator = '<Ctrl>Y'


class CopyButton(ToolButton):

    def __init__(self, **kwargs):
        ToolButton.__init__(self, 'edit-copy', **kwargs)
        self.props.tooltip_text = _('Copy')
        self.props.accelerator = '<Ctrl>C'


class PasteButton(ToolButton):

    def __init__(self, **kwargs):
        ToolButton.__init__(self, 'edit-paste', **kwargs)
        self.props.tooltip_text = _('Paste')
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


class TitleEntry(Gtk.Box):
    __gsignals__ = {
        'enter-key-press': (GObject.SignalFlags.RUN_FIRST, None, ())
    }
     
    def __init__(self, activity, **kwargs):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)
        self.set_hexpand(False)
        self.set_vexpand(False)
        self.entry = Gtk.Entry(**kwargs)
        
        # Update screen dimension handling
        display = Gdk.Display.get_default()
        monitors = display.get_monitors()
        monitor = monitors.get_item(0)
        geometry = monitor.get_geometry()
        self.entry.set_size_request(int(geometry.width / 3), -1)
        
        self.entry.set_text(activity.metadata['title'])
        self.entry.connect('notify::has-focus', self.__focus_changed_cb, activity)
        # self.entry.connect('focus-out-event', self.__focus_out_event_cb, activity)
        self.entry.connect('activate', self.__activate_cb, activity)
        self.entry.set_visible(True)
        # Use a GestureClick on the entry
        click_controller = Gtk.GestureClick()
        click_controller.connect("pressed", self.__on_entry_clicked)
        self.entry.add_controller(click_controller)
        
        self.append(self.entry)

    def __on_entry_clicked(self, gesture, n_press, x, y):
        if not self.entry.is_focus():
            self.entry.grab_focus()
            self.entry.select_region(0, -1)
        return True

    def __focus_changed_cb(self, widget, param_spec, activity):
        if not widget.has_focus():
            widget.select_region(0, 0)
            self.save_title(activity)
            
    def __focus_out_event_cb(self, widget, event, activity):
        widget.select_region(0, 0)
        self.save_title(activity)
        return False

    def __activate_cb(self, entry, activity):
        self.save_title(activity)
        entry.select_region(0, 0)
        entry.set_visible(False)
        entry.set_visible(True)
        self.emit('enter-key-press')
        return False

    def __jobject_updated_cb(self, jobject):
        if self.entry.has_focus():
            return
        if self.entry.get_text() == jobject['title']:
            return
        self.entry.set_text(jobject['title'])

    def __closing_cb(self, activity):
        self.save_title(activity)
        return False

    def __focus_out_event_cb(self, widget, event, activity):
        widget.select_region(0, 0)
        self.save_title(activity)
        return False

    def __button_press_event_cb(self, widget, event):
        if widget.is_focus():
            return False
        else:
            widget.grab_focus()
            widget.select_region(0, -1)
            return True

    def save_title(self, activity):
        title = self.entry.get_text()
        if title == activity.metadata['title']:
            return

        activity.metadata['title'] = title
        activity.metadata['title_set_by_user'] = '1'
        activity.save()

        activity.set_title(title)

        shared_activity = activity.get_shared_activity()
        if shared_activity is not None:
            shared_activity.props.name = title


class DescriptionItem(ToolButton):

    def __init__(self, activity, **kwargs):
        ToolButton.__init__(self, 'edit-description', **kwargs)
        self.set_tooltip(_('Description'))
        self.palette_invoker.props.toggle_palette = True
        self.palette_invoker.props.lock_palette = True
        self.props.hide_tooltip_on_click = False
        self._palette = self.get_palette()

        description_box = PaletteMenuBox()
        sw = Gtk.ScrolledWindow()
        display = Gdk.Display.get_default()
        monitor = display.get_monitors().get_item(0)
        geometry = monitor.get_geometry()
        sw.set_size_request(int(geometry.width / 2),
                            2 * style.GRID_CELL_SIZE)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self._text_view = Gtk.TextView()
        self._text_view.set_cursor_visible(True)
        self._text_view.set_margin_start(style.DEFAULT_PADDING)
        self._text_view.set_margin_end(style.DEFAULT_PADDING)
        self._text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_buffer = Gtk.TextBuffer()
        if 'description' in activity.metadata:
            text_buffer.set_text(activity.metadata['description'])
        self._text_view.set_buffer(text_buffer)
        # Replace "focus-out-event" with "notify::has-focus" for GTK4
        # self._text_view.connect('focus-out-event', self.__description_changed_cb, activity)
        self._text_view.connect('notify::has-focus', self.__focus_changed_cb, activity)
        sw.set_child(self._text_view)
        description_box.append_item(sw, vertical_padding=0)
        self._palette.set_content(description_box)
        description_box.set_visible(True)

        activity.metadata.connect('updated', self.__jobject_updated_cb)

    def __focus_changed_cb(self, widget, pspec, activity):
        if not widget.has_focus():
            self.__description_changed_cb(widget, None, activity)

    def __description_changed_cb(self, widget, event, activity):
        description = self._get_text_from_buffer()
        if 'description' in activity.metadata and \
                description == activity.metadata['description']:
            return
        activity.metadata['description'] = description
        activity.save()
        return False

    def set_expanded(self, expanded):
        box = self.toolbar_box
        if not box:
            return

        if not expanded:
            self.palette_invoker.notify_popdown()
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

    def _get_text_from_buffer(self):
        buf = self._text_view.get_buffer()
        start_iter = buf.get_start_iter()
        end_iter = buf.get_end_iter()
        return buf.get_text(start_iter, end_iter, False)

    def __jobject_updated_cb(self, jobject):
        if self._text_view.has_focus():
            return
        if 'description' not in jobject:
            return
        if self._get_text_from_buffer() == jobject['description']:
            return
        buf = self._text_view.get_buffer()
        buf.set_text(jobject['description'])

    def __description_changed_cb(self, widget, event, activity):
        description = self._get_text_from_buffer()
        if 'description' in activity.metadata and \
                description == activity.metadata['description']:
            return

        activity.metadata['description'] = description
        activity.save()
        return False


class ActivityToolbar(Gtk.Box):
    """The Activity toolbar with the Journal entry title and sharing button"""
    __gsignals__ = {
        'enter-key-press': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, activity, orientation_left=False):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)

        self._activity = activity

        if activity.metadata:
            title_button = TitleEntry(activity)
            title_button.connect('enter-key-press',
                                 lambda widget: self.emit('enter-key-press'))
            title_button.set_visible(True)
            self.append(title_button)

        if not orientation_left:
            separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
            separator.set_visible(True)
            separator.set_expand(True)
            self.append(separator)

        if activity.metadata:
            description_item = DescriptionItem(activity)
            description_item.set_visible(True)
            self.append(description_item)

        self.share = ShareButton(activity)
        self.share.set_visible(True)
        self.append(self.share)


class EditToolbar(Gtk.Box):
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
        self._edit_toolbar.set_visible(True)
    """

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)

        self.undo = UndoButton()
        self.append(self.undo)
        self.undo.set_visible(True)

        self.redo = RedoButton()
        self.append(self.redo)
        self.redo.set_visible(True)

        self.separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.separator.set_visible(True)
        self.append(self.separator)

        self.copy = CopyButton()
        self.append(self.copy)
        self.copy.set_visible(True)

        self.paste = PasteButton()
        self.append(self.paste)
        self.paste.set_visible(True)

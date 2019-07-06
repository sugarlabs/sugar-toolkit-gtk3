"""
Alerts appear in an activity below the toolbox and above the canvas.

:class:`Alert` and the derived :class:`TimeoutAlert`,
:class:`ConfirmationAlert`, :class:`ErrorAlert`, and
:class:`NotifyAlert`, each have a title, a message and optional
buttons.

:class:`Alert` will emit a `response` signal when a button is
clicked.

The :class:`TimeoutAlert` and :class:`NotifyAlert` display a countdown
and will emit a `response` signal when a timeout occurs.

Example:
    Create a simple alert message.

    .. code-block:: python

        from sugar3.graphics.alert import Alert

        # Create a new simple alert
        alert = Alert()

        # Set the title and text body of the alert
        alert.props.title = _('Title of Alert Goes Here')
        alert.props.msg = _('Text message of alert goes here')

        # Add the alert to the activity
        self.add_alert(alert)
        alert.show()

STABLE.
"""
# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2010, Anish Mangal <anishmangal2002@gmail.com>
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

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GLib
import math

from sugar3.graphics import style
from sugar3.graphics.icon import Icon


def _(msg):
    return gettext.dgettext('sugar-toolkit-gtk3', msg)


if not hasattr(GObject.ParamFlags, 'READWRITE'):
    GObject.ParamFlags.READWRITE = GObject.ParamFlags.WRITABLE | \
        GObject.ParamFlags.READABLE


class Alert(Gtk.EventBox):
    """
    Alerts are inside the activity window instead of being a
    separate popup window. They do not hide the canvas.

    Use :func:`~sugar3.graphics.window.Window.add_alert` and
    :func:`~sugar3.graphics.window.Window.remove_alert` to add and
    remove an alert.  These methods are inherited by an
    :class:`~sugar3.activity.activity.Activity` via superclass
    :class:`~sugar3.graphics.window.Window`.

    The alert is placed between the canvas and the toolbox, or above
    the canvas in fullscreen mode.

    Args:
        title (str): the title of the alert
        message (str): the message of the alert
        icon (str): the icon that appears at the far left
    """
    __gtype_name__ = 'SugarAlert'

    __gsignals__ = {
        'response': (GObject.SignalFlags.RUN_FIRST, None, ([object])),
    }

    __gproperties__ = {
        'title': (str, None, None, None, GObject.ParamFlags.READWRITE),
        'msg': (str, None, None, None, GObject.ParamFlags.READWRITE),
        'icon': (object, None, None, GObject.ParamFlags.WRITABLE),
    }

    def __init__(self, **kwargs):
        self._title = None
        self._msg = None
        self._icon = None
        self._buttons = {}

        self._hbox = Gtk.HBox()
        self._hbox.set_border_width(style.DEFAULT_SPACING)
        self._hbox.set_spacing(style.DEFAULT_SPACING)

        self._msg_box = Gtk.VBox()
        self._title_label = Gtk.Label()
        self._title_label.set_alignment(0, 0.5)
        self._title_label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
        self._msg_box.pack_start(self._title_label, False, False, 0)

        self._msg_label = Gtk.Label()
        self._msg_label.set_alignment(0, 0.5)
        self._msg_label.set_ellipsize(style.ELLIPSIZE_MODE_DEFAULT)
        self._msg_box.pack_start(self._msg_label, False, False, 0)
        self._hbox.pack_start(self._msg_box, False, False, 0)

        self._buttons_box = Gtk.HButtonBox()
        self._buttons_box.set_layout(Gtk.ButtonBoxStyle.END)
        self._buttons_box.set_spacing(style.DEFAULT_SPACING)
        self._hbox.pack_end(self._buttons_box, True, True, 0)

        GObject.GObject.__init__(self, **kwargs)

        self.set_visible_window(True)
        self.add(self._hbox)
        self._title_label.show()
        self._msg_label.show()
        self._buttons_box.show()
        self._msg_box.show()
        self._hbox.show()
        self.show()

    def do_set_property(self, pspec, value):
        """
        Set alert property, GObject internal method.
        Use the `alert.props` object, eg::

            alert.props.title = 'Are you happy?'
        """
        if pspec.name == 'title':
            if self._title != value:
                self._title = value
                self._title_label.set_markup('<b>' + self._title + '</b>')
        elif pspec.name == 'msg':
            if self._msg != value:
                self._msg = value
                self._msg_label.set_markup(self._msg)
                self._msg_label.set_line_wrap(True)
        elif pspec.name == 'icon':
            if self._icon != value:
                self._icon = value
                self._hbox.pack_start(self._icon, False, False, 0)
                self._hbox.reorder_child(self._icon, 0)

    def do_get_property(self, pspec):
        """
        Get alert property, GObject internal method.
        Use the `alert.props` object, eg::

            title = alert.props.title
        """
        if pspec.name == 'title':
            return self._title
        elif pspec.name == 'msg':
            return self._msg

    def add_entry(self):
        """
        Create an entry and add it to the alert.

        The entry is placed after the title and before the buttons.

        Caller is responsible for capturing the entry text in the
        `response` signal handler or a :class:`Gtk.Entry` signal
        handler.

        Returns:
            :class:`Gtk.Entry`: the entry added to the alert
        """
        entry = Gtk.Entry()
        self._hbox.pack_start(entry, True, True, 0)
        entry.show()

        self._hbox.set_child_packing(self._buttons_box, False, False, 0,
                                     Gtk.PackType.END)

        return entry

    def add_button(self, response_id, label, icon=None, position=-1):
        """
        Create a button and add it to the alert.

        The button is added to the end of the alert.

        When the button is clicked, the `response` signal will be
        emitted, along with a response identifier.

        Args:
            response_id (int): the response identifier, a
                :class:`Gtk.ResponseType` constant or any positive
                integer,
            label (str): a label for the button
            icon (:class:`~sugar3.graphics.icon.Icon` or \
                :class:`Gtk.Image`, optional):
                an icon for the button
            position (int, optional): the position of the button in
                the box of buttons,

        Returns:
            :class:`Gtk.Button`: the button added to the alert

        """
        button = Gtk.Button()
        self._buttons[response_id] = button
        if icon is not None:
            button.set_image(icon)
        button.set_label(label)
        self._buttons_box.pack_start(button, True, True, 0)
        button.show()
        button.connect('clicked', self.__button_clicked_cb, response_id)
        if position != -1:
            self._buttons_box.reorder_child(button, position)
        return button

    def remove_button(self, response_id):
        """
        Remove a button from the alert.

        The button is selected for removal using the response
        identifier that was passed to :func:`add_button`.

        Args:
            response_id (int): the response identifier

        Returns:
            None

        """
        self._buttons_box.remove(self._buttons[response_id])

    def _response(self, response_id):
        """
        Emitting response when we have a result

        A result can be that a user has clicked a button or
        a timeout has occurred, the id identifies the button
        that has been clicked and -1 for a timeout
        """
        self.emit('response', response_id)

    def __button_clicked_cb(self, button, response_id):
        self._response(response_id)


if hasattr(Alert, 'set_css_name'):
    Alert.set_css_name('alert')


class ConfirmationAlert(Alert):
    """
    An alert with two buttons; Ok and Cancel.

    When a button is clicked, the :class:`ConfirmationAlert` will emit
    a `response` signal with a response identifier.  For the Ok
    button, the response identifier will be
    :class:`Gtk.ResponseType.OK`.  For the Cancel button,
    :class:`Gtk.ResponseType.CANCEL`.

    Args:
        **kwargs: parameters for :class:`~sugar3.graphics.alert.Alert`

    .. code-block:: python

        from sugar3.graphics.alert import ConfirmationAlert

        # Create a Confirmation alert and add it to the UI.
        def _alert_confirmation(self):
            alert = ConfirmationAlert()
            alert.props.title=_('Title of Alert Goes Here')
            alert.props.msg = _('Text message of alert goes here')
            alert.connect('response', self._alert_response_cb)
            self.add_alert(alert)

        # Called when an alert object sends a response signal.
        def _alert_response_cb(self, alert, response_id):
            # Remove the alert
            self.remove_alert(alert)

            # Check the response identifier.
            if response_id is Gtk.ResponseType.OK:
                print('Ok Button was clicked.')
            elif response_id is Gtk.ResponseType.CANCEL:
                print('Cancel Button was clicked.')
    """

    def __init__(self, **kwargs):
        Alert.__init__(self, **kwargs)

        icon = Icon(icon_name='dialog-cancel')
        self.add_button(Gtk.ResponseType.CANCEL, _('Cancel'), icon)
        icon.show()

        icon = Icon(icon_name='dialog-ok')
        self.add_button(Gtk.ResponseType.OK, _('Ok'), icon)
        icon.show()


class ErrorAlert(Alert):
    """
    An alert with one button; Ok.

    When the button is clicked, the :class:`ErrorAlert` will
    emit a `response` signal with a response identifier
    :class:`Gtk.ResponseType.OK`.

    Args:
        **kwargs: parameters for :class:`~sugar3.graphics.alert.Alert`

    .. code-block:: python

        from sugar3.graphics.alert import ErrorAlert

        # Create a Error alert and add it to the UI.
        def _alert_error(self):
            alert = ErrorAlert()
            alert.props.title=_('Title of Alert Goes Here')
            alert.props.msg = _('Text message of alert goes here')
            alert.connect('response', self._alert_response_cb)
            self.add_alert(alert)

        # called when an alert object throws a response event.
        def _alert_response_cb(self, alert, response_id):
            # Remove the alert
            self.remove_alert(alert)

            # Check the response identifier.
            if response_id is Gtk.ResponseType.OK:
                print('Ok Button was clicked.')
    """

    def __init__(self, **kwargs):
        Alert.__init__(self, **kwargs)

        icon = Icon(icon_name='dialog-ok')
        self.add_button(Gtk.ResponseType.OK, _('Ok'), icon)
        icon.show()


class _TimeoutIcon(Gtk.Alignment):
    __gtype_name__ = 'SugarTimeoutIcon'

    def __init__(self):
        Gtk.Alignment.__init__(self, xalign=0, yalign=0, xscale=1, yscale=1)
        self.set_app_paintable(True)
        self._text = Gtk.Label()
        self._text.set_alignment(0.5, 0.5)
        self.add(self._text)
        self._text.show()
        self.connect('draw', self.__draw_cb)

    def __draw_cb(self, widget, context):
        self._draw(context)
        return False

    def do_get_preferred_width(self):
        width = Gtk.icon_size_lookup(Gtk.IconSize.BUTTON)[1]
        return width, width

    def do_get_preferred_height(self):
        height = Gtk.icon_size_lookup(Gtk.IconSize.BUTTON)[2]
        return height, height

    def _draw(self, context):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        x = w * 0.5
        y = h * 0.5
        radius = w / 2
        context.arc(x, y, radius, 0, 2 * math.pi)
        widget_style = self.get_style_context()
        color = widget_style.get_background_color(self.get_state_flags())
        context.set_source_rgb(color.red, color.green, color.blue)
        context.fill_preserve()

    def set_text(self, text):
        self._text.set_markup('<b>%s</b>' % GLib.markup_escape_text(str(text)))


if hasattr(_TimeoutIcon, 'set_css_name'):
    _TimeoutIcon.set_css_name('timeouticon')


class _TimeoutAlert(Alert):
    def __init__(self, timeout=5, label=_('Ok'), **kwargs):
        Alert.__init__(self, **kwargs)

        self._timeout = timeout

        self._timeout_text = _TimeoutIcon()
        self._timeout_text.set_text(self._timeout)
        self.add_button(Gtk.ResponseType.OK, label, self._timeout_text)
        self._timeout_text.show()

        self._timeout_sid = GLib.timeout_add(1000, self.__timeout_cb)

    def __timeout_cb(self):
        self._timeout -= 1
        self._timeout_text.set_text(self._timeout)
        if self._timeout == 0:
            Alert._response(self, -1)
            return False
        return True

    def _response(self, *args):
        GLib.source_remove(self._timeout_sid)
        Alert._response(self, *args)


class TimeoutAlert(_TimeoutAlert):
    """
    A timed alert with two buttons; Continue and Cancel.  The Continue
    button contains a countdown of seconds remaining.

    When a button is clicked, the :class:`TimeoutAlert` will emit
    a `response` signal with a response identifier.  For the Continue
    button, the response identifier will be
    :class:`Gtk.ResponseType.OK`.  For the Cancel button,
    :class:`Gtk.ResponseType.CANCEL`.

    If the countdown reaches zero before a button is clicked, the
    :class:`TimeoutAlert` will emit a `response` signal with a
    response identifier of -1.

    Args:
        timeout (int, optional): time in seconds, default 5
        **kwargs: parameters for :class:`~sugar3.graphics.alert.Alert`

    .. code-block:: python

        from sugar3.graphics.alert import TimeoutAlert

        # Create a Timeout alert and add it to the UI
        def _alert_timeout(self):
            alert = TimeoutAlert(timeout=10)
            alert.props.title = _('Title of Alert Goes Here')
            alert.props.msg = _('Text message of alert goes here')
            alert.connect('response', self.__alert_response_cb)
            self.add_alert(alert)

        # Called when an alert object throws a response event.
        def __alert_response_cb(self, alert, response_id):
            # Remove the alert
            self.remove_alert(alert)

            # Check the response identifier.
            if response_id is Gtk.ResponseType.OK:
                print('Continue Button was clicked.')
            elif response_id is Gtk.ResponseType.CANCEL:
                print('Cancel Button was clicked.')
            elif response_id == -1:
                print('Timeout occurred')
    """

    def __init__(self, timeout=5, **kwargs):
        _TimeoutAlert.__init__(self, timeout, _('Continue'), **kwargs)

        icon = Icon(icon_name='dialog-cancel')
        self.add_button(Gtk.ResponseType.CANCEL, _('Cancel'), icon)
        icon.show()


class NotifyAlert(_TimeoutAlert):
    """
    A timed alert with one button; Ok.  The button contains a
    countdown of seconds remaining.

    When the button is clicked, the :class:`NotifyAlert` will
    emit a `response` signal with a response identifier
    :class:`Gtk.ResponseType.OK`.

    If the countdown reaches zero before the button is clicked, the
    :class:`NotifyAlert` will emit a `response` signal with a
    response identifier of -1.

    Args:
        timeout (int, optional): time in seconds, default 5
        **kwargs: parameters for :class:`~sugar3.graphics.alert.Alert`

    .. code-block:: python

        from sugar3.graphics.alert import NotifyAlert

        # create a Notify alert then show it
        def _alert_notify(self):
            alert = NotifyAlert()
            alert.props.title = _('Title of Alert Goes Here')
            alert.props.msg = _('Text message of alert goes here')
            alert.connect('response', self._alert_response_cb)
            self.add_alert(alert)

        def __alert_response_cb(self, alert, response_id):
            # Remove the alert
            self.remove_alert(alert)

            # Check the response identifier.
            if response_id is Gtk.ResponseType.OK:
                print('Ok Button was clicked.')
            elif response_id == -1:
                print('Timeout occurred')
    """

    def __init__(self, timeout=5, **kwargs):
        _TimeoutAlert.__init__(self, timeout, _('Ok'), **kwargs)

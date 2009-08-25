"""
Alerts appear at the top of the body of your activity.

At a high level, Alert and its different variations (TimeoutAlert,
ConfirmationAlert, etc.) have a title, an alert message and then several
buttons that the user can click. The Alert class will pass "response" events
to your activity when any of these buttons are clicked, along with a
response_id to help you identify what button was clicked.


Examples
--------
create a simple alert message.

.. code-block:: python
  from sugar.graphics.alert import Alert
  ...
       # Create a new simple alert
        alert = Alert()
        # Populate the title and text body of the alert.
        alert.props.title=_('Title of Alert Goes Here')
        alert.props.msg = _('Text message of alert goes here')
        # Call the add_alert() method (inherited via the sugar.graphics.Window
        # superclass of Activity) to add this alert to the activity window.
        self.add_alert(alert)
        alert.show()

STABLE.
"""
# Copyright (C) 2007, One Laptop Per Child
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
import hippo
import math

from sugar.graphics import style
from sugar.graphics.icon import Icon


_ = lambda msg: gettext.dgettext('sugar-toolkit', msg)


class Alert(gtk.EventBox):
    """
    UI interface for Alerts

    Alerts are used inside the activity window instead of being a
    separate popup window. They do not hide canvas content. You can
    use add_alert(widget) and remove_alert(widget) inside your activity
    to add and remove the alert. The position of the alert is below the
    toolbox or top in fullscreen mode.

    Properties:
        'title': the title of the alert,
        'message': the message of the alert,
        'icon': the icon that appears at the far left

    See __gproperties__

    """

    __gtype_name__ = 'SugarAlert'

    __gsignals__ = {
        'response': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([object])),
    }

    __gproperties__ = {
        'title': (str, None, None, None, gobject.PARAM_READWRITE),
        'msg': (str, None, None, None, gobject.PARAM_READWRITE),
        'icon': (object, None, None, gobject.PARAM_WRITABLE),
    }

    def __init__(self, **kwargs):

        self._title = None
        self._msg = None
        self._icon = None
        self._buttons = {}

        self._hbox = gtk.HBox()
        self._hbox.set_border_width(style.DEFAULT_SPACING)
        self._hbox.set_spacing(style.DEFAULT_SPACING)

        self._msg_box = gtk.VBox()
        self._title_label = gtk.Label()
        self._title_label.set_alignment(0, 0.5)
        self._msg_box.pack_start(self._title_label, False)

        self._msg_label = gtk.Label()
        self._msg_label.set_alignment(0, 0.5)
        self._msg_box.pack_start(self._msg_label, False)
        self._hbox.pack_start(self._msg_box, False)

        self._buttons_box = gtk.HButtonBox()
        self._buttons_box.set_layout(gtk.BUTTONBOX_END)
        self._buttons_box.set_spacing(style.DEFAULT_SPACING)
        self._hbox.pack_start(self._buttons_box)

        gobject.GObject.__init__(self, **kwargs)

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
        Set alert property

        Parameters
        ----------
        pspec :

        value :

        Returns
        -------
        None

        """
        if pspec.name == 'title':
            if self._title != value:
                self._title = value
                self._title_label.set_markup("<b>" + self._title + "</b>")
        elif pspec.name == 'msg':
            if self._msg != value:
                self._msg = value
                self._msg_label.set_markup(self._msg)
                self._msg_label.set_line_wrap(True)
        elif pspec.name == 'icon':
            if self._icon != value:
                self._icon = value
                self._hbox.pack_start(self._icon, False)
                self._hbox.reorder_child(self._icon, 0)

    def do_get_property(self, pspec):
        """
        Get alert property

        Parameters
        ----------
        pspec :
            property for which the value will be returned

        Returns
        -------
        value of the property specified

        """
        if pspec.name == 'title':
            return self._title
        elif pspec.name == 'msg':
            return self._msg

    def add_button(self, response_id, label, icon=None, position=-1):
        """
        Add a button to the alert

        Parameters
        ----------
        response_id :
            will be emitted with the response signal a response ID should one
            of the pre-defined GTK Response Type Constants or a positive number
        label :
            that will occure right to the buttom

        icon :
            this can be a SugarIcon or a gtk.Image

        postion :
            the position of the button in the box (optional)

        Returns
        -------
        button :gtk.Button

        """
        button = gtk.Button()
        self._buttons[response_id] = button
        if icon is not None:
            button.set_image(icon)
        button.set_label(label)
        self._buttons_box.pack_start(button)
        button.show()
        button.connect('clicked', self.__button_clicked_cb, response_id)
        if position != -1:
            self._buttons_box.reorder_child(button, position)
        return button

    def remove_button(self, response_id):
        """
        Remove a button from the alert by the given response id

        Parameters
        ----------
        response_id :

        Returns
        -------
        None

        """
        self._buttons_box.remove(self._buttons[response_id])

    def _response(self, response_id):
        """Emitting response when we have a result

        A result can be that a user has clicked a button or
        a timeout has occured, the id identifies the button
        that has been clicked and -1 for a timeout
        """
        self.emit('response', response_id)

    def __button_clicked_cb(self, button, response_id):
        self._response(response_id)


class ConfirmationAlert(Alert):
    """
    This is a ready-made two button (Cancel,Ok) alert.

    A confirmation alert is a nice shortcut from a standard Alert because it
    comes with 'OK' and 'Cancel' buttons already built-in. When clicked, the
    'OK' button will emit a response with a response_id of gtk.RESPONSE_OK,
    while the 'Cancel' button will emit gtk.RESPONSE_CANCEL.

    Examples
    --------

    .. code-block:: python
      from sugar.graphics.alert import ConfirmationAlert
      ...
        #### Method: _alert_confirmation, create a Confirmation alert (with ok
                     and cancel buttons standard)
        # and add it to the UI.
        def _alert_confirmation(self):
            alert = ConfirmationAlert()
            alert.props.title=_('Title of Alert Goes Here')
            alert.props.msg = _('Text message of alert goes here')
            alert.connect('response', self._alert_response_cb)
            self.add_alert(alert)


        #### Method: _alert_response_cb, called when an alert object throws a
                     response event.
        def _alert_response_cb(self, alert, response_id):
            #remove the alert from the screen, since either a response button
            #was clicked or there was a timeout
            self.remove_alert(alert)

            #Do any work that is specific to the type of button clicked.
            if response_id is gtk.RESPONSE_OK:
                print 'Ok Button was clicked. Do any work upon ok here ...'
            elif response_id is gtk.RESPONSE_CANCEL:
                print 'Cancel Button was clicked.'

    """

    def __init__(self, **kwargs):
        Alert.__init__(self, **kwargs)

        icon = Icon(icon_name='dialog-cancel')
        self.add_button(gtk.RESPONSE_CANCEL, _('Cancel'), icon)
        icon.show()

        icon = Icon(icon_name='dialog-ok')
        self.add_button(gtk.RESPONSE_OK, _('Ok'), icon)
        icon.show()


class _TimeoutIcon(hippo.CanvasText, hippo.CanvasItem):
    """An icon with a round border"""
    __gtype_name__ = 'AlertTimeoutIcon'

    def __init__(self, **kwargs):
        hippo.CanvasText.__init__(self, **kwargs)

        self.props.orientation = hippo.ORIENTATION_HORIZONTAL
        self.props.border_left = style.DEFAULT_SPACING
        self.props.border_right = style.DEFAULT_SPACING

    def do_paint_background(self, cr, damaged_box):
        [width, height] = self.get_allocation()

        xval = width * 0.5
        yval = height * 0.5
        radius = min(width * 0.5, height * 0.5)

        hippo.cairo_set_source_rgba32(cr, self.props.background_color)
        cr.arc(xval, yval, radius, 0, 2*math.pi)
        cr.fill_preserve()


class TimeoutAlert(Alert):
    """
    This is a ready-made two button (Cancel,Continue) alert

    It times out with a positive response after the given amount of seconds.


    Examples
    --------

    .. code-block:: python
      from sugar.graphics.alert import TimeoutAlert
      ...
        #### Method: _alert_timeout, create a Timeout alert (with ok and cancel
                     buttons standard)
        # and add it to the UI.
        def _alert_timeout(self):
            #Notice that for a TimeoutAlert, you pass the number of seconds in
            #which to timeout. By default, this is 5.
            alert = TimeoutAlert(10)
            alert.props.title=_('Title of Alert Goes Here')
            alert.props.msg = _('Text message of timeout alert goes here')
            alert.connect('response', self._alert_response_cb)
            self.add_alert(alert)

        #### Method: _alert_response_cb, called when an alert object throws a
                     response event.
        def _alert_response_cb(self, alert, response_id):
            #remove the alert from the screen, since either a response button
            #was clicked or there was a timeout
            self.remove_alert(alert)

            #Do any work that is specific to the type of button clicked.
            if response_id is gtk.RESPONSE_OK:
                print 'Ok Button was clicked. Do any work upon ok here ...'
            elif response_id is gtk.RESPONSE_CANCEL:
                print 'Cancel Button was clicked.'
            elif response_id == -1:
                print 'Timout occurred'

    """

    def __init__(self, timeout=5, **kwargs):
        Alert.__init__(self, **kwargs)

        self._timeout = timeout

        icon = Icon(icon_name='dialog-cancel')
        self.add_button(gtk.RESPONSE_CANCEL, _('Cancel'), icon)
        icon.show()

        self._timeout_text = _TimeoutIcon(
            text=self._timeout,
            color=style.COLOR_BUTTON_GREY.get_int(),
            background_color=style.COLOR_WHITE.get_int())
        canvas = hippo.Canvas()
        canvas.set_root(self._timeout_text)
        canvas.show()
        self.add_button(gtk.RESPONSE_OK, _('Continue'), canvas)

        gobject.timeout_add_seconds(1, self.__timeout)

    def __timeout(self):
        self._timeout -= 1
        self._timeout_text.props.text = self._timeout
        if self._timeout == 0:
            self._response(gtk.RESPONSE_OK)
            return False
        return True


class NotifyAlert(Alert):
    """
    Timeout alert with only an "OK" button - just for notifications

    Examples
    --------

    .. code-block:: python
      from sugar.graphics.alert import NotifyAlert
      ...
        #### Method: _alert_notify, create a Notify alert (with only an 'OK'
                     button)
        # and add it to the UI.
        def _alert_notify(self):
            #Notice that for a NotifyAlert, you pass the number of seconds in
            #which to notify. By default, this is 5.
            alert = NotifyAlert(10)
            alert.props.title=_('Title of Alert Goes Here')
            alert.props.msg = _('Text message of notify alert goes here')
            alert.connect('response', self._alert_response_cb)
            self.add_alert(alert)

    """

    def __init__(self, timeout=5, **kwargs):
        Alert.__init__(self, **kwargs)

        self._timeout = timeout

        self._timeout_text = _TimeoutIcon(
            text=self._timeout,
            color=style.COLOR_BUTTON_GREY.get_int(),
            background_color=style.COLOR_WHITE.get_int())
        canvas = hippo.Canvas()
        canvas.set_root(self._timeout_text)
        canvas.show()
        self.add_button(gtk.RESPONSE_OK, _('Ok'), canvas)

        gobject.timeout_add(1000, self.__timeout)

    def __timeout(self):
        self._timeout -= 1
        self._timeout_text.props.text = self._timeout
        if self._timeout == 0:
            self._response(gtk.RESPONSE_OK)
            return False
        return True

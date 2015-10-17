# Copyright (C) 2015 Walter Bender
# Copyright (C) 2015 Sam Parkinson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA

'''
The wrapper module provides an abstraction over the sugar
collaboration system.

Using CollabWrapper
-------------------
1. Implement the `get_data` and `set_data` methods in your activity
   class::

    def get_data(self):
        # return plain python objects - things that can be encoded
        # using the json module
        return dict(
            text=self._entry.get_text()
        )

    def set_data(self, data):
        # data will be the same object returned by get_data
        self._entry.set_text(data.get('text'))

2. Make your CollabWrapper instance::

    def __init__(self, handle):
        sugar3.activity.activity.Activity.__init__(self, handle)
        self._collab = CollabWrapper(self)
        self._collab.connect('message', self.__message_cb)

        # setup your activity

        self._collab.setup()

3. Post any changes to the CollabWrapper.  The changes will be sent to
   other users if any are connected::

    def __entry_changed_cb(self, *args):
        self._collab.post(dict(
            action='entry_changed',
            new_text=self._entry.get_text()
        ))

4. Handle incoming messages::

    def __message_cb(self, collab, buddy, message):
        action = msg.get('action')
        if action == 'entry_changed':
            self._entry.set_text(msg.get('new_text'))
'''

import json
from gettext import gettext as _
from gi.repository import GObject

from telepathy.interfaces import CHANNEL_INTERFACE
from telepathy.interfaces import CHANNEL_INTERFACE_GROUP
from telepathy.interfaces import CHANNEL_TYPE_TEXT
from telepathy.interfaces import CONN_INTERFACE_ALIASING
from telepathy.constants import CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES
from telepathy.constants import CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
from telepathy.client import Connection

from sugar3.presence import presenceservice
from sugar3.activity.activity import SCOPE_PRIVATE
from sugar3.graphics.alert import NotifyAlert, Alert

import logging
_logger = logging.getLogger('text-channel-wrapper')

ACTION_INIT_REQUEST = '!!ACTION_INIT_REQUEST'
ACTION_INIT_RESPONSE = '!!ACTION_INIT_RESPONSE'


class CollabWrapper(GObject.GObject):
    '''
    The collaboration wrapper provides a high level abstraction over the
    collaboration system.  The wrapper deals with setting up the channels,
    encoding and decoding messages, initialization and alerting the user
    to the status.

    When a user joins the activity, it will query the leader for the
    contents.  The leader will return the result of the activity's
    `get_data` function which will be passed to the `set_data` function
    on the new user's computer.

    The `message` signal is called when a message is received from a
    buddy.  It has 2 arguments.  The first is the buddy, as a
    :class:`sugar3.presence.buddy.Buddy`. The second is the decoded
    content of the message, same as that posted by the other instance.

    The `joined` signal is emitted when the buddy joins a running
    activity.  If the user shares and activity, the joined signal
    is not emitted.  By the time this signal is emitted, the channels
    will be setup so all messages will flow through.

    The `buddy_joined` and `buddy_left` signals are emitted when
    another user joins or leaves the activity.  They both a
    :class:`sugar3.presence.buddy.Buddy` as their only argument.
    '''

    message = GObject.Signal('message', arg_types=[object, object])
    joined = GObject.Signal('joined')
    buddy_joined = GObject.Signal('buddy_joined', arg_types=[object])
    buddy_left = GObject.Signal('buddy_left', arg_types=[object])

    def __init__(self, activity):
        GObject.GObject.__init__(self)
        self.activity = activity
        self.shared_activity = activity.shared_activity
        self._leader = False
        self._init_waiting = False
        self._text_channel = None

    def setup(self):
        '''
        Setup must be called to so that the activity can join or share
        if appropriate.

        .. note::
            As soon as setup is called, any signal, `get_data` or
            `set_data` call must be made.  This means that your
            activity must have set up enough so these functions can
            work.
        '''
        # Some glue to know if we are launching, joining, or resuming
        # a shared activity.
        if self.shared_activity:
            # We're joining the activity.
            self.activity.connect("joined", self.__joined_cb)

            if self.activity.get_shared():
                _logger.debug('calling _joined_cb')
                self.__joined_cb(self)
            else:
                _logger.debug('Joining activity...')
                self._alert(_('Joining activity...'),
                            _('Please wait for the connection...'))
        else:
            if not self.activity.metadata or self.activity.metadata.get(
                    'share-scope', SCOPE_PRIVATE) == \
                    SCOPE_PRIVATE:
                # We are creating a new activity instance.
                _logger.debug('Off-line')
            else:
                # We are sharing an old activity instance.
                _logger.debug('On-line')
                self._alert(_('Resuming shared activity...'),
                            _('Please wait for the connection...'))
            self.activity.connect('shared', self.__shared_cb)

    def _alert(self, title, msg=None):
        a = NotifyAlert()
        a.props.title = title
        a.props.msg = msg
        self.activity.add_alert(a)
        a.connect('response', lambda a, r: self.activity.remove_alert(a))
        a.show()

    def __shared_cb(self, sender):
        ''' Callback for when activity is shared. '''
        self.shared_activity = self.activity.shared_activity
        self._setup_text_channel()

        self._leader = True
        _logger.debug('I am sharing...')

    def __joined_cb(self, sender):
        '''Callback for when an activity is joined.'''
        self.shared_activity = self.activity.shared_activity
        if not self.shared_activity:
            return

        self._setup_text_channel()
        self._init_waiting = True
        self.post({'action': ACTION_INIT_REQUEST})

        _logger.debug('I joined a shared activity.')
        self.joined.emit()

    def _setup_text_channel(self):
        ''' Set up a text channel to use for collaboration. '''
        self._text_channel = _TextChannelWrapper(
            self.shared_activity.telepathy_text_chan,
            self.shared_activity.telepathy_conn)

        # Tell the text channel what callback to use for incoming
        # text messages.
        self._text_channel.set_received_callback(self.__received_cb)

        # Tell the text channel what callbacks to use when buddies
        # come and go.
        self.shared_activity.connect('buddy-joined', self.__buddy_joined_cb)
        self.shared_activity.connect('buddy-left', self.__buddy_left_cb)

    def __received_cb(self, buddy, msg):
        '''Process a message when it is received.'''
        action = msg.get('action')
        if action == ACTION_INIT_REQUEST and self._leader:
            data = self.activity.get_data()
            self.post({'action': ACTION_INIT_RESPONSE, 'data': data})
            return
        elif action == ACTION_INIT_RESPONSE and self._init_waiting:
            data = msg['data']
            self.activity.set_data(data)
            self._init_waiting = False
            return

        if buddy:
            nick = buddy.props.nick
        else:
            nick = '???'
        _logger.debug('Received message from %s: %r', nick, msg)
        self.message.emit(buddy, msg)

    def post(self, msg):
        '''
        Broadcast a message to the other buddies if the activity is
        shared.  If it is not shared, the message will not be send
        at all.

        Args:
            msg (object): json encodable object to send to the other
                buddies, eg. :class:`dict` or :class:`str`.
        '''
        _logger.debug('Posting msg %r', msg)
        if self._text_channel is not None:
            _logger.debug('\tActually posting post')
            self._text_channel.post(msg)

    def __buddy_joined_cb(self, sender, buddy):
        '''A buddy joined.'''
        self.buddy_joined.emit(buddy)

    def __buddy_left_cb(self, sender, buddy):
        '''A buddy left.'''
        self.buddy_left.emit(buddy)


class _TextChannelWrapper(object):
    '''Wrapper for a telepathy Text Channel'''

    def __init__(self, text_chan, conn):
        '''Connect to the text channel'''
        self._activity_cb = None
        self._activity_close_cb = None
        self._text_chan = text_chan
        self._conn = conn
        self._signal_matches = []
        m = self._text_chan[CHANNEL_INTERFACE].connect_to_signal(
            'Closed', self._closed_cb)
        self._signal_matches.append(m)

    def post(self, msg):
        if msg is not None:
            _logger.debug('post')
            self._send(json.dumps(msg))

    def _send(self, text):
        '''Send text over the Telepathy text channel.'''
        _logger.debug('sending %s' % text)

        if self._text_chan is not None:
            self._text_chan[CHANNEL_TYPE_TEXT].Send(
                CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, text)

    def close(self):
        '''Close the text channel.'''
        _logger.debug('Closing text channel')
        try:
            self._text_chan[CHANNEL_INTERFACE].Close()
        except Exception:
            _logger.debug('Channel disappeared!')
            self._closed_cb()

    def _closed_cb(self):
        '''Clean up text channel.'''
        for match in self._signal_matches:
            match.remove()
        self._signal_matches = []
        self._text_chan = None
        if self._activity_close_cb is not None:
            self._activity_close_cb()

    def set_received_callback(self, callback):
        '''Connect the function callback to the signal.

        callback -- callback function taking buddy and text args
        '''
        if self._text_chan is None:
            return
        self._activity_cb = callback
        m = self._text_chan[CHANNEL_TYPE_TEXT].connect_to_signal(
            'Received', self._received_cb)
        self._signal_matches.append(m)

    def handle_pending_messages(self):
        '''Get pending messages and show them as received.'''
        for identity, timestamp, sender, type_, flags, text in \
            self._text_chan[
                CHANNEL_TYPE_TEXT].ListPendingMessages(False):
            self._received_cb(identity, timestamp, sender, type_, flags, text)

    def _received_cb(self, identity, timestamp, sender, type_, flags, text):
        '''Handle received text from the text channel.

        Converts sender to a Buddy.
        Calls self._activity_cb which is a callback to the activity.
        '''
        _logger.debug('received_cb %r %s' % (type_, text))
        if type_ != 0:
            # Exclude any auxiliary messages
            return

        msg = json.loads(text)

        if self._activity_cb:
            try:
                self._text_chan[CHANNEL_INTERFACE_GROUP]
            except Exception:
                # One to one XMPP chat
                nick = self._conn[
                    CONN_INTERFACE_ALIASING].RequestAliases([sender])[0]
                buddy = {'nick': nick, 'color': '#000000,#808080'}
                _logger.error('Exception: recieved from sender %r buddy %r' %
                              (sender, buddy))
            else:
                # XXX: cache these
                buddy = self._get_buddy(sender)
                _logger.error('Else: recieved from sender %r buddy %r' %
                              (sender, buddy))

            self._activity_cb(buddy, msg)
            self._text_chan[
                CHANNEL_TYPE_TEXT].AcknowledgePendingMessages([identity])
        else:
            _logger.debug('Throwing received message on the floor'
                          ' since there is no callback connected. See'
                          ' set_received_callback')

    def set_closed_callback(self, callback):
        '''Connect a callback for when the text channel is closed.

        callback -- callback function taking no args

        '''
        _logger.debug('set closed callback')
        self._activity_close_cb = callback

    def _get_buddy(self, cs_handle):
        '''Get a Buddy from a (possibly channel-specific) handle.'''
        # XXX This will be made redundant once Presence Service
        # provides buddy resolution

        # Get the Presence Service
        pservice = presenceservice.get_instance()

        # Get the Telepathy Connection
        tp_name, tp_path = pservice.get_preferred_connection()
        conn = Connection(tp_name, tp_path)
        group = self._text_chan[CHANNEL_INTERFACE_GROUP]
        my_csh = group.GetSelfHandle()
        if my_csh == cs_handle:
            handle = conn.GetSelfHandle()
        elif (group.GetGroupFlags() &
              CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES):
            handle = group.GetHandleOwners([cs_handle])[0]
        else:
            handle = cs_handle

            # XXX: deal with failure to get the handle owner
            assert handle != 0

        return pservice.get_buddy_by_telepathy_handle(
            tp_name, tp_path, handle)

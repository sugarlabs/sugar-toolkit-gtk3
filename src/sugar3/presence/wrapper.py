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

from telepathy.interfaces import \
    CHANNEL_INTERFACE, \
    CHANNEL_INTERFACE_GROUP, \
    CHANNEL_TYPE_TEXT, \
    CHANNEL_TYPE_FILE_TRANSFER, \
    CONN_INTERFACE_ALIASING, \
    CHANNEL, \
    CLIENT
from telepathy.constants import \
    CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES, \
    CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
from telepathy.client import Connection

from sugar3.presence import presenceservice
from sugar3.activity.activity import SCOPE_PRIVATE
from sugar3.graphics.alert import NotifyAlert
from sugar3.presence.filetransfer import \
    IncomingFileTransfer, \
    OutgoingBlobTransfer, \
    OutgoingFileTransfer, \
    FT_STATE_COMPLETED

import logging

ACTION_INIT_REQUEST = '!!ACTION_INIT_REQUEST'
ACTION_INIT_RESPONSE = '!!ACTION_INIT_RESPONSE'
ACTIVITY_FT_MIME = 'x-sugar/from-activity'


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




    '''

    message = GObject.Signal('message', arg_types=[object, object])
    '''
    The `message` signal is called when a message is received from a
    buddy.  It has 2 arguments.  The first is the buddy, as a
    :class:`sugar3.presence.buddy.Buddy`. The second is the decoded
    content of the message, same as that posted by the other instance.
    '''

    joined = GObject.Signal('joined')
    '''
    The `joined` signal is emitted when the buddy joins a running
    activity.  If the user shares and activity, the joined signal
    is not emitted.  By the time this signal is emitted, the channels
    will be setup so all messages will flow through.
    '''

    buddy_joined = GObject.Signal('buddy_joined', arg_types=[object])
    '''
    The `buddy_joined` signal is emitted when another user joins the
    activity. The only argument is a
    :class:`sugar3.presence.buddy.Buddy`, for the buddy that joined.
    '''

    buddy_left = GObject.Signal('buddy_left', arg_types=[object])
    '''
    The `buddy_left` signal is emitted when another user leaves the
    activity. The only argument is a
    :class:`sugar3.presence.buddy.Buddy`, for the buddy that left.
    '''

    incoming_file = GObject.Signal('incoming_file', arg_types=[object, object])
    '''
    The `incoming_file` signal is emitted when a file transfer is
    received from another buddy.  The first argument is the object representing
    the transfer, as a
    :class:`sugar3.presence.filetransfer.IncomingFileTransfer`.  The 2nd
    argument is the description, as passed to the `send_file_*` function
    by the sender.
    '''

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
            work.  For example, place this at the end of the activity's
            `__init__` function.
        '''
        # Some glue to know if we are launching, joining, or resuming
        # a shared activity.
        if self.shared_activity:
            # We're joining the activity.
            self.activity.connect("joined", self.__joined_cb)

            if self.activity.get_shared():
                logging.debug('calling _joined_cb')
                self.__joined_cb(self)
            else:
                logging.debug('Joining activity...')
                self._alert(_('Joining activity...'),
                            _('Please wait for the connection...'))
        else:
            if not self.activity.metadata or self.activity.metadata.get(
                    'share-scope', SCOPE_PRIVATE) == \
                    SCOPE_PRIVATE:
                # We are creating a new activity instance.
                logging.debug('Off-line')
            else:
                # We are sharing an old activity instance.
                logging.debug('On-line')
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
        self._listen_for_channels()

        self._leader = True
        logging.debug('I am sharing...')

    def __joined_cb(self, sender):
        '''Callback for when an activity is joined.'''
        self.shared_activity = self.activity.shared_activity
        if not self.shared_activity:
            return

        self._setup_text_channel()
        self._listen_for_channels()
        self._init_waiting = True
        self.post({'action': ACTION_INIT_REQUEST})

        logging.debug('I joined a shared activity.')
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

    def _listen_for_channels(self):
        conn = self.shared_activity.telepathy_conn
        conn.connect_to_signal('NewChannels', self.__new_channels_cb)

    def __new_channels_cb(self, channels):
        conn = self.shared_activity.telepathy_conn
        for path, props in channels:
            if props[CHANNEL + '.Requested']:
                continue  # This channel was requested by me

            channel_type = props[CHANNEL + '.ChannelType']
            if channel_type == CHANNEL_TYPE_FILE_TRANSFER:
                self._handle_ft_channel(conn, path, props)

    def _handle_ft_channel(self, conn, path, props):
        ft = IncomingFileTransfer(conn, path, props)
        if ft.description == ACTION_INIT_RESPONSE:
            ft.connect('notify::state', self.__notify_ft_state_cb)
            ft.accept_to_memory()
        else:
            desc = json.loads(ft.description)
            self.incoming_file.emit(ft, desc)

    def __notify_ft_state_cb(self, ft, pspec):
        if ft.props.state == FT_STATE_COMPLETED and self._init_waiting:
            stream = ft.props.output
            stream.close(None)
            # FIXME:  The data prop seems to just be the raw pointer
            gbytes = stream.steal_as_bytes()
            data = gbytes.get_data()
            logging.debug('Got init data from buddy:  %s', data)
            data = json.loads(data)
            self.activity.set_data(data)
            self._init_waiting = False

    def __received_cb(self, buddy, msg):
        '''Process a message when it is received.'''
        action = msg.get('action')
        if action == ACTION_INIT_REQUEST and self._leader:
            data = self.activity.get_data()
            data = json.dumps(data)
            OutgoingBlobTransfer(
                buddy,
                self.shared_activity.telepathy_conn,
                data,
                self.get_client_name(),
                ACTION_INIT_RESPONSE,
                ACTIVITY_FT_MIME)
            return

        if buddy:
            nick = buddy.props.nick
        else:
            nick = '???'
        logging.debug('Received message from %s: %r', nick, msg)
        self.message.emit(buddy, msg)

    def send_file_memory(self, buddy, data, description):
        '''
        Send a 1-to-1 transfer from memory to a given buddy.  They will
        get the file transfer and description through the `incoming_transfer`
        signal.

        Args:
            buddy (sugar3.presence.buddy.Buddy): buddy to offer the transfer to
            data (str): the data to offer to the buddy via the transfer
            description (object): a json encodable description for the
                transfer.  This will be given to the `incoming_transfer` signal
                of the transfer
        '''
        OutgoingBlobTransfer(
            buddy,
            self.shared_activity.telepathy_conn,
            data,
            self.get_client_name(),
            json.dumps(description),
            ACTIVITY_FT_MIME)

    def send_file_file(self, buddy, path, description):
        '''
        Send a 1-to-1 transfer from a file to a given buddy.  They will
        get the file transfer and description through the `incoming_transfer`
        signal.

        Args:
            buddy (sugar3.presence.buddy.Buddy): buddy to offer the transfer to
            path (str): path of the file to send to the buddy
            description (object): a json encodable description for the
                transfer.  This will be given to the `incoming_transfer` signal
                of the transfer
        '''
        OutgoingFileTransfer(
            buddy,
            self.shared_activity.telepathy_conn,
            path,
            self.get_client_name(),
            json.dumps(description),
            ACTIVITY_FT_MIME)

    def post(self, msg):
        '''
        Broadcast a message to the other buddies if the activity is
        shared.  If it is not shared, the message will not be send
        at all.

        Args:
            msg (object): json encodable object to send to the other
                buddies, eg. :class:`dict` or :class:`str`.
        '''
        if self._text_channel is not None:
            self._text_channel.post(msg)

    def __buddy_joined_cb(self, sender, buddy):
        '''A buddy joined.'''
        self.buddy_joined.emit(buddy)

    def __buddy_left_cb(self, sender, buddy):
        '''A buddy left.'''
        self.buddy_left.emit(buddy)

    def get_client_name(self):
        '''
        Get the name of the activity's telepathy client.

        Returns: str, telepathy client name
        '''
        return CLIENT + '.' + self.activity.get_bundle_id()


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
            logging.debug('post')
            self._send(json.dumps(msg))

    def _send(self, text):
        '''Send text over the Telepathy text channel.'''
        logging.debug('sending %s' % text)

        if self._text_chan is not None:
            self._text_chan[CHANNEL_TYPE_TEXT].Send(
                CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, text)

    def close(self):
        '''Close the text channel.'''
        logging.debug('Closing text channel')
        try:
            self._text_chan[CHANNEL_INTERFACE].Close()
        except Exception:
            logging.debug('Channel disappeared!')
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
        logging.debug('received_cb %r %s' % (type_, text))
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
                logging.debug('exception: recieved from sender %r buddy %r' %
                              (sender, buddy))
            else:
                # XXX: cache these
                buddy = self._get_buddy(sender)
                logging.debug('Else: recieved from sender %r buddy %r' %
                              (sender, buddy))

            self._activity_cb(buddy, msg)
            self._text_chan[
                CHANNEL_TYPE_TEXT].AcknowledgePendingMessages([identity])
        else:
            logging.debug('Throwing received message on the floor'
                          ' since there is no callback connected. See'
                          ' set_received_callback')

    def set_closed_callback(self, callback):
        '''Connect a callback for when the text channel is closed.

        callback -- callback function taking no args

        '''
        logging.debug('set closed callback')
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

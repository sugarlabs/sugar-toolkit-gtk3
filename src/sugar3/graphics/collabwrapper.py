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

import os
import json
import socket
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib
import dbus

from telepathy.interfaces import \
    CHANNEL_INTERFACE, \
    CHANNEL_INTERFACE_GROUP, \
    CHANNEL_TYPE_TEXT, \
    CHANNEL_TYPE_FILE_TRANSFER, \
    CONN_INTERFACE_ALIASING, \
    CONNECTION_INTERFACE_REQUESTS, \
    CHANNEL, \
    CLIENT
from telepathy.constants import \
    CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES, \
    CONNECTION_HANDLE_TYPE_CONTACT, \
    CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, \
    CONNECTION_HANDLE_TYPE_CONTACT, \
    SOCKET_ADDRESS_TYPE_UNIX, \
    SOCKET_ACCESS_CONTROL_LOCALHOST
from telepathy.client import Connection, Channel

from sugar3.presence import presenceservice
from sugar3.activity.activity import SCOPE_PRIVATE
from sugar3.graphics.alert import NotifyAlert, Alert

import logging
_logger = logging.getLogger('text-channel-wrapper')

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

    The `incoming_file` signal is emitted when a file transfer is
    received from a buddy.  The first argument is the object representing
    the transfer, as a
    :class:`sugar3.presence.filetransfer.IncomingFileTransfer`.  The seccond
    argument is the description, as passed to the `send_file_*` function
    on the sender's client
    '''

    message = GObject.Signal('message', arg_types=[object, object])
    joined = GObject.Signal('joined')
    buddy_joined = GObject.Signal('buddy_joined', arg_types=[object])
    buddy_left = GObject.Signal('buddy_left', arg_types=[object])
    incoming_file = GObject.Signal('incoming_file', arg_types=[object, object])

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
        self._listen_for_channels()

        self._leader = True
        _logger.debug('I am sharing...')

    def __joined_cb(self, sender):
        '''Callback for when an activity is joined.'''
        self.shared_activity = self.activity.shared_activity
        if not self.shared_activity:
            return

        self._setup_text_channel()
        self._listen_for_channels()
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
        _logger.debug('Received message from %s: %r', nick, msg)
        self.message.emit(buddy, msg)

    def send_file_memory(self, buddy, data, description):
        '''
        Send a 1-to-1 transfer from memory to a given buddy.  They will
        get the file transfer and description through the `incoming_transfer`
        signal.

        Args:
            buddy (sugar3.presence.buddy.Buddy), buddy to offer the transfer to
            data (str), the data to offer to the buddy via the transfer
            description (object), a json encodable description for the
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
            buddy (sugar3.presence.buddy.Buddy), buddy to offer the transfer to
            path (str), path of the file to send to the buddy
            description (object), a json encodable description for the
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


FT_STATE_NONE = 0
FT_STATE_PENDING = 1
FT_STATE_ACCEPTED = 2
FT_STATE_OPEN = 3
FT_STATE_COMPLETED = 4
FT_STATE_CANCELLED = 5

FT_REASON_NONE = 0
FT_REASON_REQUESTED = 1
FT_REASON_LOCAL_STOPPED = 2
FT_REASON_REMOTE_STOPPED = 3
FT_REASON_LOCAL_ERROR = 4
FT_REASON_LOCAL_ERROR = 5
FT_REASON_REMOTE_ERROR = 6


class _BaseFileTransfer(GObject.GObject):
    '''
    The base file transfer should not be used directly.  It is used as a
    base class for the incoming and outgoing file transfers.

    Props:
        filename (str), metadata provided by the buddy
        file_size (str), size of the file being sent/received, in bytes
        description (str), metadata provided by the buddy
        mime_type (str), metadata provided by the buddy
        buddy (:class:`sugar3.presence.buddy.Buddy`), other party
            in the transfer
        reason_last_change (FT_REASON_*), reason for the last state change

    GObject Props:
        state (FT_STATE_*), current state of the transfer
        transferred_bytes (int), number of bytes transfered so far
    '''


    def __init__(self):
        GObject.GObject.__init__(self)
        self._state = FT_STATE_NONE
        self._transferred_bytes = 0

        self.channel = None
        self.buddy = None
        self.filename = None
        self.file_size = None
        self.description = None
        self.mime_type = None
        self.reason_last_change = FT_REASON_NONE

    def set_channel(self, channel):
        '''
        Setup the file transfer to use a given telepathy channel.  This
        should only be used by direct subclasses of the base file transfer.
        '''
        self.channel = channel
        self.channel[CHANNEL_TYPE_FILE_TRANSFER].connect_to_signal(
            'FileTransferStateChanged', self.__state_changed_cb)
        self.channel[CHANNEL_TYPE_FILE_TRANSFER].connect_to_signal(
            'TransferredBytesChanged', self.__transferred_bytes_changed_cb)
        self.channel[CHANNEL_TYPE_FILE_TRANSFER].connect_to_signal(
            'InitialOffsetDefined', self.__initial_offset_defined_cb)

        channel_properties = self.channel[dbus.PROPERTIES_IFACE]

        props = channel_properties.GetAll(CHANNEL_TYPE_FILE_TRANSFER)
        self._state = props['State']
        self.filename = props['Filename']
        self.file_size = props['Size']
        self.description = props['Description']
        self.mime_type = props['ContentType']

    def __transferred_bytes_changed_cb(self, transferred_bytes):
        logging.debug('__transferred_bytes_changed_cb %r', transferred_bytes)
        self.props.transferred_bytes = transferred_bytes

    def _set_transferred_bytes(self, transferred_bytes):
        self._transferred_bytes = transferred_bytes

    def _get_transferred_bytes(self):
        return self._transferred_bytes

    transferred_bytes = GObject.property(type=int,
                                         default=0,
                                         getter=_get_transferred_bytes,
                                         setter=_set_transferred_bytes)

    def __initial_offset_defined_cb(self, offset):
        logging.debug('__initial_offset_defined_cb %r', offset)
        self.initial_offset = offset

    def __state_changed_cb(self, state, reason):
        logging.debug('__state_changed_cb %r %r', state, reason)
        self.reason_last_change = reason
        self.props.state = state

    def _set_state(self, state):
        self._state = state

    def _get_state(self):
        return self._state

    state = GObject.property(type=int, getter=_get_state, setter=_set_state)

    def cancel(self):
        '''
        Request that telepathy close the file transfer channel

        Spec:  http://telepathy.freedesktop.org/spec/Channel.html#Method:Close
        '''
        self.channel[CHANNEL].Close()


class IncomingFileTransfer(_BaseFileTransfer):
    '''
    An incoming file transfer from another buddy.  You need to first accept
    the transfer (either to memory or to a file).  Then you need to listen
    to the state and wait until the transfer is completed.  Then you can
    read the file that it was saved to, or access the
    :class:`Gio.MemoryOutputStream` from the `output` property.

    The `output` property is different depending on how the file was accepted.
    If the file was accepted to a file on the file system, it is a string
    representing the path to the file.  If the file was accepted to memory,
    it is a :class:`Gio.MemoryOutputStream`.
    '''

    def __init__(self, connection, object_path, props):
        _BaseFileTransfer.__init__(self)

        channel = Channel(connection.bus_name, object_path)
        self.set_channel(channel)

        self.connect('notify::state', self.__notify_state_cb)

        self._destination_path = None
        self._output_stream = None
        self._socket_address = None
        self._socket = None
        self._splicer = None

    def accept_to_file(self, destination_path):
        '''
        Accept the file transfer and write it to a new file.  The file must
        already exist.

        Args:
            destination_path (str): the path where a new file will be
                created and saved to
        '''
        if os.path.exists(destination_path):
            raise ValueError('Destination path already exists: %r' %
                             destination_path)

        self._destination_path = destination_path
        self._accept()

    def accept_to_memory(self):
        '''
        Accept the file transfer.  Once the state is FT_STATE_OPEN, a
        :class:`Gio.MemoryOutputStream` accessible via the output prop.
        '''
        self._accept()

    def _accept(self):
        channel_ft = self.channel[CHANNEL_TYPE_FILE_TRANSFER]
        self._socket_address = channel_ft.AcceptFile(
            SOCKET_ADDRESS_TYPE_UNIX,
            SOCKET_ACCESS_CONTROL_LOCALHOST,
            '',
            0,
            byte_arrays=True)

    def __notify_state_cb(self, file_transfer, pspec):
        logging.debug('__notify_state_cb %r', self.props.state)
        if self.props.state == FT_STATE_OPEN:
            # Need to hold a reference to the socket so that python doesn't
            # close the fd when it goes out of scope
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.connect(self._socket_address)
            input_stream = Gio.UnixInputStream.new(self._socket.fileno(), True)

            if self._destination_path is not None:
                destination_file = Gio.File.new_for_path(
                    self._destination_path)
                if self.initial_offset == 0:
                    self._output_stream = destination_file.create(
                        Gio.FileCreateFlags.PRIVATE, None)
                else:
                    self._output_stream = destination_file.append_to()
            else:
                self._output_stream = Gio.MemoryOutputStream.new_resizable()

            self._output_stream.splice_async(
                input_stream,
                Gio.OutputStreamSpliceFlags.CLOSE_SOURCE |
                Gio.OutputStreamSpliceFlags.CLOSE_TARGET,
                GLib.PRIORITY_LOW, None, None, None)

    @GObject.Property
    def output(self):
        return self._destination_path or self._output_stream


class _BaseOutgoingTransfer(_BaseFileTransfer):
    '''
    This class provides the base of an outgoing file transfer.

    You can override the `_get_input_stream` method to return any type of
    Gio input stream.  This will then be used to provide the file if
    requested by the application.  You also need to call `_create_channel`
    with the length of the file in bytes during your `__init__`.

    Args:
        buddy (sugar3.presence.buddy.Buddy), who to send the transfer to
        conn (telepathy.client.conn.Connection), telepathy connection to
            use to send the transfer.  Eg. `shared_activity.telepathy_conn`
        filename (str), metadata sent to the receiver
        description (str), metadata sent to the receiver
        mime (str), metadata sent to the receiver
    '''

    def __init__(self, buddy, conn, filename, description, mime):
        _BaseFileTransfer.__init__(self)
        self.connect('notify::state', self.__notify_state_cb)

        self._socket_address = None
        self._socket = None
        self._splicer = None
        self._conn = conn
        self._filename = filename
        self._description = description
        self._mime = mime
        self.buddy = buddy

    def _create_channel(self, file_size):
        object_path, properties_ = self._conn.CreateChannel(dbus.Dictionary({
            CHANNEL + '.ChannelType': CHANNEL_TYPE_FILE_TRANSFER,
            CHANNEL + '.TargetHandleType': CONNECTION_HANDLE_TYPE_CONTACT,
            CHANNEL + '.TargetHandle': self.buddy.contact_handle,
            CHANNEL_TYPE_FILE_TRANSFER + '.Filename': self._filename,
            CHANNEL_TYPE_FILE_TRANSFER + '.Description': self._description,
            CHANNEL_TYPE_FILE_TRANSFER + '.Size': file_size,
            CHANNEL_TYPE_FILE_TRANSFER + '.ContentType': self._mime,
            CHANNEL_TYPE_FILE_TRANSFER + '.InitialOffset': 0}, signature='sv'))
        self.set_channel(Channel(self._conn.bus_name, object_path))

        channel_file_transfer = self.channel[CHANNEL_TYPE_FILE_TRANSFER]
        self._socket_address = channel_file_transfer.ProvideFile(
            SOCKET_ADDRESS_TYPE_UNIX, SOCKET_ACCESS_CONTROL_LOCALHOST, '',
            byte_arrays=True)

    def _get_input_stream(self):
        raise NotImplementedError()

    def __notify_state_cb(self, file_transfer, pspec):
        if self.props.state == FT_STATE_OPEN:
            # Need to hold a reference to the socket so that python doesn't
            # closes the fd when it goes out of scope
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.connect(self._socket_address)
            output_stream = Gio.UnixOutputStream.new(
                self._socket.fileno(), True)

            input_stream = self._get_input_stream()
            output_stream.splice_async(
                input_stream,
                Gio.OutputStreamSpliceFlags.CLOSE_SOURCE |
                Gio.OutputStreamSpliceFlags.CLOSE_TARGET,
                GLib.PRIORITY_LOW, None, None, None)


class OutgoingFileTransfer(_BaseOutgoingTransfer):
    '''
    An outgoing file transfer to send from a file (on the computer's file
    system).

    Note that the `path` argument is the path for the file that will be
    sent, whereas the `filename` argument is only for metadata.

    Args:
        path (str), path of the file to send
    '''

    def __init__(self, buddy, conn, path, filename, description, mime):
        _BaseOutgoingTransfer.__init__(
            self, buddy, conn, filename, description, mime)

        self._path = path
        file_size = os.stat(path).st_size
        self._create_channel(file_size)

    def _get_input_stream(self):
        input_stream = Gio.File.new_for_path(self._path).read(None)


class OutgoingBlobTransfer(_BaseOutgoingTransfer):
    '''
    An outgoing file transfer to send from a string in memory.

    Args:
        blob (str), data to send
    '''

    def __init__(self, buddy, conn, blob, filename, description, mime):
        _BaseOutgoingTransfer.__init__(
            self, buddy, conn, filename, description, mime)

        self._blob = blob
        self._create_channel(len(self._blob))

    def _get_input_stream(self):
        return Gio.MemoryInputStream.new_from_data(self._blob, None)


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
                _logger.debug('exception: recieved from sender %r buddy %r' %
                              (sender, buddy))
            else:
                # XXX: cache these
                buddy = self._get_buddy(sender)
                _logger.debug('Else: recieved from sender %r buddy %r' %
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


# Copyright (C) 2008 Tomeu Vizoso
# Based on jarabe.model.filetransfer
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
The filetransfer module provides a high level API accepting and
sending file transfers to/from either memory of real files.

.. note ::
    This module provides options that activities should not use as they
    will trigger functions in the shell.  Activities should use the
    file transfer APIs in the :class:`sugar3.presence.wrapper.CollabWrapper`.
'''

import os
import socket

from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib
import dbus

from telepathy.interfaces import \
    CHANNEL_TYPE_FILE_TRANSFER, \
    CHANNEL
from telepathy.constants import \
    CONNECTION_HANDLE_TYPE_CONTACT, \
    SOCKET_ADDRESS_TYPE_UNIX, \
    SOCKET_ACCESS_CONTROL_LOCALHOST
from telepathy.client import Channel

import logging

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


class BaseFileTransfer(GObject.GObject):
    '''
    The base file transfer should not be used directly.  It is used as a
    base class for the incoming and outgoing file transfers.
    '''

    filename = None
    '(str): metadata provided by the buddy'

    description = None
    '(str): metadata provided by the buddy'

    file_size = None
    '(int): size of the file being sent/received, in bytes'

    mime_type = None
    '(str): metadata provided by the buddy'

    buddy = None
    '(:class:`sugar3.presence.buddy.Buddy`): other party in the transfer'

    reason_last_change = FT_REASON_NONE
    '(FT_REASON_*): reason for the last state change'

    def __init__(self):
        GObject.GObject.__init__(self)
        self._state = FT_STATE_NONE
        self._transferred_bytes = 0
        self.channel = None

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
    '(GObject Prop) (int): number of bytes transfered so far'

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
    '(GObject Prop) (FT_STATE_*): current state of the transfer'

    def cancel(self):
        '''
        Request that telepathy close the file transfer channel

        Spec:  http://telepathy.freedesktop.org/spec/Channel.html#Method:Close
        '''
        self.channel[CHANNEL].Close()


class IncomingFileTransfer(BaseFileTransfer):
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
        BaseFileTransfer.__init__(self)

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


class BaseOutgoingTransfer(BaseFileTransfer):
    '''
    This class provides the base of an outgoing file transfer.

    You can override the `_get_input_stream` method to return any type of
    Gio input stream.  This will then be used to provide the file if
    requested by the application.  You also need to call `_create_channel`
    with the length of the file in bytes during your `__init__`.

    Args:
        buddy (sugar3.presence.buddy.Buddy): who to send the transfer to
        conn (telepathy.client.conn.Connection): telepathy connection to
            use to send the transfer.  Eg. `shared_activity.telepathy_conn`
        filename (str): metadata sent to the receiver
        description (str): metadata sent to the receiver
        mime (str): metadata sent to the receiver
    '''

    def __init__(self, buddy, conn, filename, description, mime):
        BaseFileTransfer.__init__(self)
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


class OutgoingFileTransfer(BaseOutgoingTransfer):
    '''
    An outgoing file transfer to send from a file (on the computer's file
    system).

    Note that the `path` argument is the path for the file that will be
    sent, whereas the `filename` argument is only for metadata.

    Args:
        path (str): path of the file to send
    '''

    def __init__(self, buddy, conn, path, filename, description, mime):
        BaseOutgoingTransfer.__init__(
            self, buddy, conn, filename, description, mime)

        self._path = path
        file_size = os.stat(path).st_size
        self._create_channel(file_size)

    def _get_input_stream(self):
        logging.debug('opening %s for reading', self._file_name)
        return Gio.File.new_for_path(self._file_name).read(None)


class OutgoingBlobTransfer(BaseOutgoingTransfer):
    '''
    An outgoing file transfer to send from a string in memory.

    Args:
        blob (str): data to send
    '''

    def __init__(self, buddy, conn, blob, filename, description, mime):
        BaseOutgoingTransfer.__init__(
            self, buddy, conn, filename, description, mime)

        self._blob = blob
        self._create_channel(len(self._blob))

    def _get_input_stream(self):
        return Gio.MemoryInputStream.new_from_data(self._blob, None)

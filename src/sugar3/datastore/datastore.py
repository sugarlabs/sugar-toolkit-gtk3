# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2010, Simon Schampijer
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

"""
STABLE
"""

import six
import logging
import time
from datetime import datetime
import os
import tempfile
from gi.repository import GObject
from gi.repository import Gio
import dbus

from sugar3 import env
from sugar3 import mime
from sugar3 import dispatch
from sugar3.profile import get_color

DS_DBUS_SERVICE = 'org.laptop.sugar.DataStore'
DS_DBUS_INTERFACE = 'org.laptop.sugar.DataStore'
DS_DBUS_PATH = '/org/laptop/sugar/DataStore'

_data_store = None


def _get_data_store():
    global _data_store

    if not _data_store:
        _bus = dbus.SessionBus()
        _data_store = dbus.Interface(_bus.get_object(DS_DBUS_SERVICE,
                                                     DS_DBUS_PATH),
                                     DS_DBUS_INTERFACE)
        _data_store.connect_to_signal('Created', __datastore_created_cb)
        _data_store.connect_to_signal('Deleted', __datastore_deleted_cb)
        _data_store.connect_to_signal('Updated', __datastore_updated_cb)

    return _data_store


def __datastore_created_cb(object_id):
    metadata = _get_data_store().get_properties(object_id, byte_arrays=True)
    created.send(None, object_id=object_id, metadata=metadata)


def __datastore_updated_cb(object_id):
    metadata = _get_data_store().get_properties(object_id, byte_arrays=True)
    updated.send(None, object_id=object_id, metadata=metadata)


def __datastore_deleted_cb(object_id):
    deleted.send(None, object_id=object_id)


created = dispatch.Signal()
deleted = dispatch.Signal()
updated = dispatch.Signal()


class DSMetadata(GObject.GObject):
    """A representation of the metadata associated with a DS entry."""
    __gsignals__ = {
        'updated': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, properties=None):
        GObject.GObject.__init__(self)
        if not properties:
            self._properties = {}
        else:
            if six.PY3:
                for x, y in list(properties.items()):
                    try:
                        properties[x] = y.decode()
                    except BaseException:
                        pass
            self._properties = properties

        default_keys = ['activity', 'activity_id',
                        'mime_type', 'title_set_by_user']
        for key in default_keys:
            if key not in self._properties:
                self._properties[key] = ''

    def __getitem__(self, key):
        return self._properties[key]

    def __setitem__(self, key, value):
        if six.PY3:
            try:
                value = value.decode()
            except BaseException:
                pass
        if key not in self._properties or self._properties[key] != value:
            self._properties[key] = value
            self.emit('updated')

    def __delitem__(self, key):
        del self._properties[key]

    def __contains__(self, key):
        return self._properties.__contains__(key)

    def has_key(self, key):
        logging.warning(".has_key() is deprecated, use 'in'")
        return key in self._properties

    def keys(self):
        return list(self._properties.keys())

    def get_dictionary(self):
        return self._properties

    def copy(self):
        return DSMetadata(self._properties.copy())

    def get(self, key, default=None):
        if key in self._properties:
            return self._properties[key]
        else:
            return default

    def update(self, properties):
        """Update all of the metadata"""
        for (key, value) in list(properties.items()):
            self[key] = value


class DSObject(object):
    """A representation of a DS entry."""

    def __init__(self, object_id, metadata=None, file_path=None):
        self._update_signal_match = None
        self._object_id = None

        self.set_object_id(object_id)

        self._metadata = metadata
        self._file_path = file_path
        self._destroyed = False
        self._owns_file = False

    def get_object_id(self):
        return self._object_id

    def set_object_id(self, object_id):
        if self._update_signal_match is not None:
            self._update_signal_match.remove()
        if object_id is not None:
            self._update_signal_match = _get_data_store().connect_to_signal(
                'Updated', self.__object_updated_cb, arg0=object_id)

        self._object_id = object_id

    object_id = property(get_object_id, set_object_id)

    def __object_updated_cb(self, object_id):
        properties = _get_data_store().get_properties(self._object_id,
                                                      byte_arrays=True)
        self._metadata.update(properties)

    def get_metadata(self):
        if self._metadata is None and self.object_id is not None:
            properties = _get_data_store().get_properties(self.object_id)
            metadata = DSMetadata(properties)
            self._metadata = metadata
        return self._metadata

    def set_metadata(self, metadata):
        if self._metadata != metadata:
            self._metadata = metadata

    metadata = property(get_metadata, set_metadata)

    def get_file_path(self, fetch=True):
        if fetch and self._file_path is None and self.object_id is not None:
            self.set_file_path(_get_data_store().get_filename(self.object_id))
            self._owns_file = True
        return self._file_path

    def set_file_path(self, file_path):
        if self._file_path != file_path:
            if self._file_path and self._owns_file:
                if os.path.isfile(self._file_path):
                    os.remove(self._file_path)
                self._owns_file = False
            self._file_path = file_path

    file_path = property(get_file_path, set_file_path)

    def destroy(self):
        if self._destroyed:
            logging.warning('This DSObject has already been destroyed!.')
            return
        self._destroyed = True
        if self._file_path and self._owns_file:
            if os.path.isfile(self._file_path):
                os.remove(self._file_path)
            self._owns_file = False
        self._file_path = None

    def __del__(self):
        if not self._destroyed:
            logging.warning('DSObject was deleted without cleaning up first. '
                            'Call DSObject.destroy() before disposing it.')
            self.destroy()

    def copy(self):
        return DSObject(None, self._metadata.copy(), self._file_path)


class RawObject(object):
    """A representation for objects not in the DS but
    in the file system.

    """

    def __init__(self, file_path):
        stat = os.stat(file_path)
        metadata = {
            'uid': file_path,
            'title': os.path.basename(file_path),
            'timestamp': stat.st_mtime,
            'mime_type': Gio.content_type_guess(file_path, None)[0],
            'activity': '',
            'activity_id': '',
            'icon-color': get_color().to_string(),
            'description': file_path,
        }

        self.object_id = file_path
        self._metadata = DSMetadata(metadata)
        self._file_path = None
        self._destroyed = False

    def get_metadata(self):
        return self._metadata

    metadata = property(get_metadata)

    def get_file_path(self, fetch=True):
        # we have to create symlink since its a common practice
        # to create hardlinks to jobject files
        # and w/o this, it wouldn't work since we have file from mounted device
        if self._file_path is None:
            data_path = os.path.join(env.get_profile_path(), 'data')
            self._file_path = tempfile.mktemp(
                prefix='rawobject', dir=data_path)
            if not os.path.exists(data_path):
                os.makedirs(data_path)
            os.symlink(self.object_id, self._file_path)
        return self._file_path

    file_path = property(get_file_path)

    def destroy(self):
        if self._destroyed:
            logging.warning('This RawObject has already been destroyed!.')
            return
        self._destroyed = True
        if self._file_path is not None:
            if os.path.exists(self._file_path):
                os.remove(self._file_path)
            self._file_path = None

    def __del__(self):
        if not self._destroyed:
            logging.warning('RawObject was deleted without cleaning up. '
                            'Call RawObject.destroy() before disposing it.')
            self.destroy()


def get(object_id):
    """Get the properties of the object with the ID given.

    Keyword arguments:
    object_id -- unique identifier of the object

    Return: a DSObject

    """
    logging.debug('datastore.get')

    if object_id.startswith('/'):
        return RawObject(object_id)

    metadata = _get_data_store().get_properties(object_id, byte_arrays=True)

    ds_object = DSObject(object_id, DSMetadata(metadata), None)
    # TODO: register the object for updates
    return ds_object


def create():
    """Create a new DSObject.

    Return: a DSObject

    """
    metadata = DSMetadata()
    metadata['mtime'] = datetime.now().isoformat()
    metadata['timestamp'] = int(time.time())
    return DSObject(object_id=None, metadata=metadata, file_path=None)


def _update_ds_entry(uid, properties, filename, transfer_ownership=False,
                     reply_handler=None, error_handler=None, timeout=-1):
    debug_properties = properties.copy()
    if 'preview' in debug_properties:
        debug_properties['preview'] = '<omitted>'
    logging.debug('dbus_helpers.update: %s, %s, %s, %s', uid, filename,
                  debug_properties, transfer_ownership)
    if reply_handler and error_handler:
        _get_data_store().update(uid, dbus.Dictionary(properties), filename,
                                 transfer_ownership,
                                 reply_handler=reply_handler,
                                 error_handler=error_handler,
                                 timeout=timeout)
    else:
        _get_data_store().update(uid, dbus.Dictionary(properties),
                                 filename, transfer_ownership)


def _create_ds_entry(properties, filename, transfer_ownership=False):
    object_id = _get_data_store().create(dbus.Dictionary(properties), filename,
                                         transfer_ownership)
    return object_id


def write(ds_object, update_mtime=True, transfer_ownership=False,
          reply_handler=None, error_handler=None, timeout=-1):
    """Write the DSObject given to the datastore. Creates a new entry if
    the entry does not exist yet.

    Keyword arguments:
    update_mtime -- boolean if the mtime of the entry should be regenerated
                    (default True)
    transfer_ownership -- set it to true if the ownership of the entry should
                          be passed - who is responsible to delete the file
                          when done with it (default False)
    reply_handler -- will be called with the method's return values as
                     arguments (default None)
    error_handler -- will be called with an instance of a DBusException
                     representing a remote exception (default None)
    timeout -- dbus timeout for the caller to wait (default -1)

    """
    logging.debug('datastore.write')

    properties = ds_object.metadata.get_dictionary().copy()

    if update_mtime:
        properties['mtime'] = datetime.now().isoformat()
        properties['timestamp'] = int(time.time())

    file_path = ds_object.get_file_path(fetch=False)
    if file_path is None:
        file_path = ''

    # FIXME: this func will be sync for creates regardless of the handlers
    # supplied. This is very bad API, need to decide what to do here.
    if ds_object.object_id:
        _update_ds_entry(ds_object.object_id,
                         properties,
                         file_path,
                         transfer_ownership,
                         reply_handler=reply_handler,
                         error_handler=error_handler,
                         timeout=timeout)
    else:
        if reply_handler or error_handler:
            logging.warning('datastore.write() cannot currently be called'
                            'async for creates, see ticket 3071')
        ds_object.object_id = _create_ds_entry(properties, file_path,
                                               transfer_ownership)
        ds_object.metadata['uid'] = ds_object.object_id
        # TODO: register the object for updates
    logging.debug('Written object %s to the datastore.', ds_object.object_id)


def delete(object_id):
    """Delete the datastore entry with the given uid.

    Keyword arguments:
    object_id -- uid of the datastore entry

    """
    logging.debug('datastore.delete')
    _get_data_store().delete(object_id)


def find(query, sorting=None, limit=None, offset=None, properties=None,
         reply_handler=None, error_handler=None):
    """Find DS entries that match the query provided.

    Keyword arguments:
    query -- a dictionary containing metadata key value pairs
             for a fulltext search use the key 'query' e.g. {'query': 'blue*'}
             other possible well-known properties are:
             'activity':          'my.organization.MyActivity'
             'activity_id':       '6f7f3acacca87886332f50bdd522d805f0abbf1f'
             'title':             'My new project'
             'title_set_by_user': '0'
             'keep':              '0'
             'ctime':             '1972-05-12T18:41:08'
             'mtime':             '2007-06-16T03:42:33'
             'timestamp':         1192715145
             'preview':           ByteArray(png file data, 300x225 px)
             'icon-color':        '#ff0000,#ffff00'
             'mime_type':         'application/x-my-activity'
             'share-scope':       # if shared
             'buddies':           '{}'
             'description':       'some longer text'
             'tags':              'one two'
    sorting -- key to order results by e.g. 'timestamp' (default None)
    limit -- return only limit results (default None)
    offset -- return only results starting at offset (default None)
    properties -- you can specify here a list of metadata you want to be
                  present in the result e.g. ['title, 'keep'] (default None)
    reply_handler -- will be called with the method's return values as
                     arguments (default None)
    error_handler -- will be called with an instance of a DBusException
                     representing a remote exception (default None)

    Return: DSObjects matching the query, number of matches

    """
    query = query.copy()

    if properties is None:
        properties = []

    if sorting:
        query['order_by'] = sorting
    if limit:
        query['limit'] = limit
    if offset:
        query['offset'] = offset

    if reply_handler and error_handler:
        _get_data_store().find(query, properties,
                               reply_handler=reply_handler,
                               error_handler=error_handler,
                               byte_arrays=True)
        return
    else:
        entries, total_count = _get_data_store().find(query, properties,
                                                      byte_arrays=True)
    ds_objects = []
    for entry in entries:
        object_id = entry['uid']
        del entry['uid']

        ds_object = DSObject(object_id, DSMetadata(entry), None)
        ds_objects.append(ds_object)

    return ds_objects, total_count


def copy(ds_object, mount_point):
    """Copy a datastore entry

    Keyword arguments:
    ds_object -- DSObject to copy
    mount_point -- mount point of the new datastore entry

    Returns:
    new_ds_object -- DSObject copied

    """
    new_ds_object = ds_object.copy()
    new_ds_object.metadata['mountpoint'] = mount_point

    if 'title' in ds_object.metadata:
        filename = ds_object.metadata['title']

        if 'mime_type' in ds_object.metadata:
            mime_type = ds_object.metadata['mime_type']
            extension = mime.get_primary_extension(mime_type)
            if extension:
                filename += '.' + extension

        new_ds_object.metadata['suggested_filename'] = filename

    # this will cause the file be retrieved from the DS
    new_ds_object.file_path = ds_object.file_path

    write(new_ds_object)

    return new_ds_object


def get_unique_values(key):
    """Retrieve an array of unique values for a field.

    Keyword arguments:
    key -- only the property activity is currently supported

    Return: list of activities

    """
    return _get_data_store().get_uniquevaluesfor(
        key, dbus.Dictionary({}, signature='ss'))

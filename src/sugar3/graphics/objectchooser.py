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

"""
STABLE.
"""

import six
import logging
import cairo

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
import dbus

from sugar3.datastore import datastore
from sugar3.activity.activity import PREVIEW_SIZE


J_DBUS_SERVICE = 'org.laptop.Journal'
J_DBUS_INTERFACE = 'org.laptop.Journal'
J_DBUS_PATH = '/org/laptop/Journal'

FILTER_TYPE_MIME_BY_ACTIVITY = 'mime_by_activity'
FILTER_TYPE_GENERIC_MIME = 'generic_mime'
FILTER_TYPE_ACTIVITY = 'activity'


def get_preview_pixbuf(preview_data, width=-1, height=-1):
    """
    Retrive a pixbuf with the content of the preview field

    Args:
        metadata (dictionary): preview data from the metadata dictionary. Can't
            be None. Returned from the
            sugar3.datastore.datastore.DSObject.get_metadata() method.

    Keyword Args:
        width (int): the pixbuf width, if is not set,
        the default width will be used
        height (int): the pixbuf width, if is not set,
        the default height will be used

    Returns:
        Pixbuf, the generated Pixbuf
        None, if it could not be created

    Example:
        pixbuf = get_preview_pixbuf(metadata.get('preview', ''))
        has_preview = pixbuf is not None

        if has_preview:
            im = Gtk.Image()
            im.set_from_pixbuf(pixbuf)
            box.add(im)
            im.show()
    """
    if width == -1:
        width = PREVIEW_SIZE[0]

    if height == -1:
        height = PREVIEW_SIZE[1]

    pixbuf = None

    if len(preview_data) > 4:
        if preview_data[1:4] != b'PNG':
            # TODO: We are close to be able to drop this.
            import base64
            preview_data = base64.b64decode(preview_data)

        png_file = six.BytesIO(preview_data)
        try:
            # Load image and scale to dimensions
            surface = cairo.ImageSurface.create_from_png(png_file)
            png_width = surface.get_width()
            png_height = surface.get_height()

            preview_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                                 width, height)
            cr = cairo.Context(preview_surface)

            scale_w = width * 1.0 / png_width
            scale_h = height * 1.0 / png_height
            scale = min(scale_w, scale_h)

            cr.scale(scale, scale)

            cr.set_source_rgba(1, 1, 1, 0)
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.paint()
            cr.set_source_surface(surface)
            cr.paint()

            pixbuf = Gdk.pixbuf_get_from_surface(preview_surface, 0, 0,
                                                 width, height)
        except Exception:
            logging.exception('Error while loading the preview')

    return pixbuf


class ObjectChooser(object):
    """
    UI interface for object choosers.

    Object choosers can be used by acivities to allow the
    user to select objects from the file system or from
    some other similar source.

    Keyword Args:
        parent (:class:`Gtk.Widget`): the widget calling ObjectChooser

        what_filter (str): an activity bundle_id or a generic mime type as
            defined in :mod:`sugar3.mime` used to determine which objects
            will be presented in the object chooser

        filter_type (str): should be one of [None, FILTER_TYPE_GENERIC_MIME,
            FILTER_TYPE_ACTIVITY, FILTER_TYPE_MIME_BY_ACTIVITY]

            If filter_type is None, the default behavior of the
            what_filter is applied (for backward compatibility),
            this option is DEPRECATED.

            If filter_type is FILTER_TYPE_GENERIC_MIME, the
            what_filter should be a generic mime type defined in
            mime.py; the object chooser will filter based in the
            'mime_type' metadata field.

            If filter_type is FILTER_TYPE_ACTIVITY, the what_filter
            should by an activity bundle_id; the object chooser
            will filter based in the 'activity' metadata field.

            If filter_type is FILTER_TYPE_MIME_BY_ACTIVITY, the
            what_filter should be an activity bundle_id; the object
            chooser will filter based on the 'mime_type' metadata
            field and the mime types defined by the activity in the
            activity.info file.

        show_preview (bool): if True will show the preview image asociated with
            the object in the Journal. This option is only available if
            filter_type is selected.

    Examples:
        chooser = ObjectChooser(self._activity, what_filter='Image')

        chooser = ObjectChooser(parent=self,
                                what_filter=self.get_bundle_id(),
                                filter_type=FILTER_TYPE_ACTIVITY)
    """

    def __init__(self, parent=None, what_filter=None, filter_type=None,
                 show_preview=False):
        if parent is None:
            parent_xid = 0
        elif hasattr(parent, 'get_window') and hasattr(parent.get_window(),
                                                       'get_xid'):
            parent_xid = parent.get_window().get_xid()
        else:
            parent_xid = parent

        self._parent_xid = parent_xid
        self._show_preview = show_preview
        self._main_loop = None
        self._object_id = None
        self._bus = None
        self._chooser_id = None
        self._response_code = Gtk.ResponseType.NONE
        self._what_filter = what_filter
        if filter_type is not None:
            # verify is one of the availables types
            # add here more types if needed
            if filter_type not in [FILTER_TYPE_MIME_BY_ACTIVITY,
                                   FILTER_TYPE_GENERIC_MIME,
                                   FILTER_TYPE_ACTIVITY]:
                raise Exception('filter_type not implemented')

        self._filter_type = filter_type

    def run(self):
        """
        Runs the object chooser and displays it.

        Returns:
            Gtk.ResponseType constant, the response received
            from displaying the object chooser.
        """
        self._object_id = None

        self._main_loop = GObject.MainLoop()

        self._bus = dbus.SessionBus(mainloop=self._main_loop)
        self._bus.add_signal_receiver(
            self.__name_owner_changed_cb,
            signal_name='NameOwnerChanged',
            dbus_interface='org.freedesktop.DBus',
            arg0=J_DBUS_SERVICE)

        obj = self._bus.get_object(J_DBUS_SERVICE, J_DBUS_PATH)
        journal = dbus.Interface(obj, J_DBUS_INTERFACE)
        journal.connect_to_signal('ObjectChooserResponse',
                                  self.__chooser_response_cb)
        journal.connect_to_signal('ObjectChooserCancelled',
                                  self.__chooser_cancelled_cb)

        if self._what_filter is None:
            what_filter = ''
        else:
            what_filter = self._what_filter

        if self._filter_type is None:
            self._chooser_id = journal.ChooseObject(
                self._parent_xid, what_filter)
        else:
            self._chooser_id = journal.ChooseObjectWithFilter(
                self._parent_xid, what_filter, self._filter_type,
                self._show_preview)

        Gdk.threads_leave()
        try:
            self._main_loop.run()
        finally:
            Gdk.threads_enter()
        self._main_loop = None

        return self._response_code

    def get_selected_object(self):
        """
        Gets the object selected using the object chooser.

        Returns:
            object, the object selected
        """
        if self._object_id is None:
            return None
        else:
            return datastore.get(self._object_id)

    def destroy(self):
        """
        Destroys and cleans up (disposes) the object chooser.
        """
        self._cleanup()

    def _cleanup(self):
        if self._main_loop is not None:
            self._main_loop.quit()
            self._main_loop = None
        self._bus = None

    def __chooser_response_cb(self, chooser_id, object_id):
        if chooser_id != self._chooser_id:
            return
        logging.debug('ObjectChooser.__chooser_response_cb: %r' % object_id)
        self._response_code = Gtk.ResponseType.ACCEPT
        self._object_id = object_id
        self._cleanup()

    def __chooser_cancelled_cb(self, chooser_id):
        if chooser_id != self._chooser_id:
            return
        logging.debug('ObjectChooser.__chooser_cancelled_cb: %r' % chooser_id)
        self._response_code = Gtk.ResponseType.CANCEL
        self._cleanup()

    def __name_owner_changed_cb(self, name, old, new):
        logging.debug('ObjectChooser.__name_owner_changed_cb')
        # Journal service disappeared from the bus
        self._response_code = Gtk.ResponseType.CANCEL
        self._cleanup()

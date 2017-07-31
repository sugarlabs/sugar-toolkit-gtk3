# Copyright (C) 2013 Daniel Narvaez
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

import json
import os
import logging

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.0')

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import WebKit2
from gi.repository import Gtk
from gi.repository import GdkX11
assert GdkX11

from sugar3.graphics.objectchooser import ObjectChooser
from gi.repository import SugarExt
from sugar3.activity import activity


class FilePicker(ObjectChooser):
    def __init__(self, parent):
        ObjectChooser.__init__(self, parent)

    def run(self):
        jobject = None
        _file = None
        try:
            result = ObjectChooser.run(self)
            if result == Gtk.ResponseType.ACCEPT:
                jobject = self.get_selected_object()
                logging.debug('FilePicker.run: %r', jobject)

                if jobject and jobject.file_path:
                    _file = jobject.file_path
                    logging.debug('FilePicker.run: file=%r', _file)
        finally:
            if jobject is not None:
                jobject.destroy()

        return _file


class WebActivity(Gtk.Window):
    def __init__(self, handle):
        Gtk.Window.__init__(self)

        self._activity_id = handle.activity_id
        self._object_id = handle.object_id
        self._bundle_id = os.environ["SUGAR_BUNDLE_ID"]
        self._bundle_path = os.environ["SUGAR_BUNDLE_PATH"]
        self._inspector_visible = False

        self.set_decorated(False)
        self.maximize()

        self.connect("key-press-event", self._key_press_event_cb)
        self.connect('realize', self._realize_cb)
        self.connect('destroy', self._destroy_cb)

        context = WebKit2.WebContext.get_default()
        context.register_uri_scheme("activity", self._app_scheme_cb, None)

        self._web_view = WebKit2.WebView()
        self._web_view.connect("load-changed", self._loading_changed_cb)
        self._web_view.connect('run-file-chooser', self.__run_file_chooser)

        self.add(self._web_view)
        self._web_view.show()

        settings = self._web_view.get_settings()
        settings.set_property("enable-developer-extras", True)

        self._web_view.load_uri("activity://%s/index.html" % self._bundle_id)

        self.set_title(activity.get_bundle_name())

    def run_main_loop(self):
        Gtk.main()

    def _realize_cb(self, window):
        xid = window.get_window().get_xid()
        SugarExt.wm_set_bundle_id(xid, self._bundle_id)
        SugarExt.wm_set_activity_id(xid, str(self._activity_id))

    def _destroy_cb(self, window):
        self.destroy()
        Gtk.main_quit()

    def _loading_changed_cb(self, web_view, load_event):
        if load_event == WebKit2.LoadEvent.FINISHED:
            key = os.environ["SUGAR_APISOCKET_KEY"]
            port = os.environ["SUGAR_APISOCKET_PORT"]

            env_json = json.dumps({"apiSocketKey": key,
                                   "apiSocketPort": port,
                                   "activityId": self._activity_id,
                                   "bundleId": self._bundle_id,
                                   "objectId": self._object_id,
                                   "activityName": activity.get_bundle_name()})

            script = """
                     var environment = %s;

                     if (window.sugar === undefined) {
                         window.sugar = {};
                     }

                     window.sugar.environment = environment;

                     if (window.sugar.onEnvironmentSet)
                         window.sugar.onEnvironmentSet();
                    """ % env_json

            self._web_view.run_javascript(script, None, None, None)

    def __run_file_chooser(self, browser, request):
        picker = FilePicker(self)
        chosen = picker.run()
        picker.destroy()

        if chosen:
            request.select_files([chosen])
        else:
            request.cancel()
        return True

    def _key_press_event_cb(self, window, event):
        key_name = Gdk.keyval_name(event.keyval)

        if event.get_state() & Gdk.ModifierType.CONTROL_MASK and \
           event.get_state() & Gdk.ModifierType.SHIFT_MASK:
            if key_name == "I":
                inspector = self._web_view.get_inspector()
                if self._inspector_visible:
                    inspector.close()
                    self._inspector_visible = False
                else:
                    inspector.show()
                    self._inspector_visible = True

                return True

    def _app_scheme_cb(self, request, user_data):
        path = os.path.join(self._bundle_path,
                            os.path.relpath(request.get_path(), "/"))

        request.finish(Gio.File.new_for_path(path).read(None),
                       -1, Gio.content_type_guess(path, None)[0])

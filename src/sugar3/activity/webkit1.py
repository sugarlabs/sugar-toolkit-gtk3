# Copyright (C) 2013 Gonzalo Odiard
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

from gi.repository import Gtk
from gi.repository import GdkX11
assert GdkX11

from gi.repository import GObject
GObject.threads_init()
from gi.repository import WebKit
import socket
from threading import Thread
from six.moves.BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from six.moves import socketserver
import select
import errno
import mimetypes

from gi.repository import SugarExt
from sugar3.activity import activity
from sugar3.graphics.objectchooser import ObjectChooser


class LocalRequestHandler(BaseHTTPRequestHandler):

    # Handler for the GET requests
    def do_GET(self):
        new_path = self.server.path + self.path
        if not os.path.exists(new_path):
            logging.error('file %s not found.', new_path)
            self.send_response(404)
            self.end_headers()
            return False

        with open(new_path) as f:
            content = f.read()
        self.send_response(200)
        mime, _encoding = mimetypes.guess_type(self.path)
        self.send_header("Content-type", mime)
        self.end_headers()
        self.wfile.write(content)
        return False


class LocalHTTPServer(HTTPServer):

    def __init__(self, server_address, request_handler, path):
        self.path = path
        HTTPServer.__init__(self, server_address, request_handler)

    def serve_forever(self, poll_interval=0.5):
        """Overridden version of BaseServer.serve_forever that
        does not fail to work when EINTR is received.
        """
        self._BaseServer__serving = True
        self._BaseServer__is_shut_down.clear()
        while self._BaseServer__serving:

            # XXX: Consider using another file descriptor or
            # connecting to the socket to wake this up instead of
            # polling. Polling reduces our responsiveness to a
            # shutdown request and wastes cpu at all other times.
            try:
                r, w, e = select.select([self], [], [], poll_interval)
            except select.error as e:
                if e[0] == errno.EINTR:
                    logging.debug("got eintr")
                    continue
                raise
            if r:
                self._handle_request_noblock()
        self._BaseServer__is_shut_down.set()

    def server_bind(self):
        """Override server_bind in HTTPServer to not use
        getfqdn to get the server name because is very slow."""
        socketserver.TCPServer.server_bind(self)
        _host, port = self.socket.getsockname()[:2]
        self.server_name = 'localhost'
        self.server_port = port


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

        self.connect('realize', self._realize_cb)
        self.connect('destroy', self._destroy_cb)

        # Get a free socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 0))
        sock.listen(socket.SOMAXCONN)
        _ipaddr, self.port = sock.getsockname()
        sock.shutdown(socket.SHUT_RDWR)
        logging.error('Using port %d', self.port)

        # start the local web server
        httpd = LocalHTTPServer(('', self.port),
                                lambda *args: LocalRequestHandler(*args),
                                activity.get_bundle_path())
        self._server = Thread(target=httpd.serve_forever)
        self._server.setDaemon(True)
        self._server.start()

        self._web_view = WebKit.WebView()
        self._web_view.connect("notify::load-status",
                               self._loading_changed_cb)
        self._web_view.connect("resource-request-starting",
                               self._resource_request_starting_cb)
        try:
            self._web_view.connect('run-file-chooser', self.__run_file_chooser)
        except TypeError:
            # Only present in WebKit1 > 1.9.3 and WebKit2
            pass

        self.add(self._web_view)
        self._web_view.show()

        self._web_view.load_uri("activity://%s/index.html" % self._bundle_id)

        self.set_title(activity.get_bundle_name())

    def run_main_loop(self):
        Gtk.main()

    def _resource_request_starting_cb(self, webview, web_frame, web_resource,
                                      request, response):
        # this is used only in the case of webkit1
        uri = web_resource.get_uri()
        if uri.startswith('activity://'):
            prefix = "activity://%s" % self._bundle_id
            new_prefix = "http://0.0.0.0:%d" % self.port
            new_uri = new_prefix + uri[len(prefix):]

            request.set_uri(new_uri)

    def _realize_cb(self, window):
        xid = window.get_window().get_xid()
        SugarExt.wm_set_bundle_id(xid, self._bundle_id)
        SugarExt.wm_set_activity_id(xid, str(self._activity_id))

    def _destroy_cb(self, window):
        self.destroy()
        Gtk.main_quit()

    def _loading_changed_cb(self, web_view, load_event):

        status = web_view.get_load_status()

        if status == WebKit.LoadStatus.FINISHED:
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

            self._web_view.execute_script(script)

    def __run_file_chooser(self, browser, request):
        picker = FilePicker(self)
        chosen = picker.run()
        picker.destroy()

        if chosen:
            request.select_files([chosen])
        return True

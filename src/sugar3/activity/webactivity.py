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

USE_WEBKIT1 = 'SUGAR_USE_WEBKIT1' in os.environ

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GdkX11
assert GdkX11

if USE_WEBKIT1:
    from gi.repository import GObject
    GObject.threads_init()
    from gi.repository import WebKit
    import socket
    from threading import Thread
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    import SocketServer
    import select
    import errno
    import mimetypes
else:
    from gi.repository import WebKit2

from gi.repository import SugarExt
from sugar3.activity import activity


if USE_WEBKIT1:

    class LocalRequestHandler(BaseHTTPRequestHandler):

        #Handler for the GET requests
        def do_GET(self):
            new_path = self.server.path + '/' + self.path
            if not os.path.exists(new_path):
                logging.error('file %s not found.', new_path)
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
                except select.error, e:
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
            SocketServer.TCPServer.server_bind(self)
            _host, port = self.socket.getsockname()[:2]
            self.server_name = 'localhost'
            self.server_port = port


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

        if USE_WEBKIT1:
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
        else:
            context = WebKit2.WebContext.get_default()
            context.register_uri_scheme("activity", self._app_scheme_cb, None)

            self._web_view = WebKit2.WebView()
            self._web_view.connect("load-changed", self._loading_changed_cb)

            settings = self._web_view.get_settings()
            settings.set_property("enable-developer-extras", True)

            self.connect("key-press-event", self._key_press_event_cb)

        self.add(self._web_view)
        self._web_view.show()

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

    def _resource_request_starting_cb(self, webview, web_frame, web_resource,
                                      request, response):
        # this is used only in the case of webkit1
        uri = web_resource.get_uri()
        if uri.startswith('activity://'):
            prefix = "activity://%s" % self._bundle_id
            new_prefix = "http://0.0.0.0:%d" % self.port
            new_uri = new_prefix + uri[len(prefix):]

            request.set_uri(new_uri)

    def _loading_changed_cb(self, web_view, load_event):

        finished = False
        if USE_WEBKIT1:
            status = web_view.get_load_status()
            finished = (status == WebKit.LoadStatus.FINISHED)
        else:
            finished = (load_event == WebKit2.LoadEvent.FINISHED)

        if finished:
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

            if USE_WEBKIT1:
                self._web_view.execute_script(script)
            else:
                self._web_view.run_javascript(script, None, None, None)

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

# Copyright (C) 2013 Gonzalo Odiard
# Copyright (C) 2016 Sam Parkinson <sam@sam.today>
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

import tempfile
from urlparse import urlparse

from gi.repository import SoupGNOME
from gi.repository import GObject
from gi.repository import WebKit
from gi.repository import GLib
from gi.repository import Gio

from sugar3.graphics.webkit.shared import FilePicker


# Fake WebKitLoadEvent enum
class LoadEvent():
    STARTED = 0
    REDIRECTED = 10
    COMMITTED = 20
    FINISHED = 30

    MAPPING = {
        WebKit.LoadStatus.PROVISIONAL: STARTED,
        WebKit.LoadStatus.COMMITTED: COMMITTED,
        WebKit.LoadStatus.FINISHED: FINISHED,
    }


class _FakeWebKitURISchemeRequest():
    def __init__(self, scheme, webview, web_resource, request):
        self._web_resource = web_resource
        self._web_view = webview
        self._request = request
        self._scheme = scheme

    def get_uri(self):
        return self._web_resource.get_uri()

    def get_path(self):
        return urlparse(self.get_uri()).path

    def get_scheme(self):
        return self._scheme

    def get_webview(self):
        return self._webview

    def finish(self, input_stream, stream_length, mime):
        # FIXME:  How do we know when webkit is done with the files?
        outp = tempfile.NamedTemporaryFile(delete=False)

        while True:
            read_bytes = input_stream.read_bytes(8192, None)
            if read_bytes.get_size() == 0:
                break
            # Hack
            data = read_bytes.get_data()
            if '</head>' in data:
                data = data.replace('</head>', '<base href="{}" /></head>'.format(self.get_uri()))
            outp.write(data)

        self._request.set_uri('file://' + outp.name)


class WebView(WebKit.WebView):

    needs_scrolled_window = True

    load_changed_signal = GObject.Signal('load-changed', arg_types=[int])
    '''
    This signal mirrors the WebKit2.WebView "load-changed" signal
    '''

    def __init__(self, **kwargs):
        WebKit.WebView.__init__(self, **kwargs)
        self.set_full_content_zoom(True)
        self.connect('resource-request-starting', self.__resource_request_starting_cb)
        self._uri_schemes = {}
        self.connect('notify::load-status', self.__load_status_changed_cb)
        try:
            self.connect('run-file-chooser', self.__run_file_chooser)
        except TypeError:
            # Only present in WebKit1 > 1.9.3 and WebKit2
            pass

    def __run_file_chooser(self, browser, request):
        picker = FilePicker(self)
        chosen = picker.run()
        picker.destroy()

        if chosen:
            request.select_files([chosen])
        return True

    @staticmethod
    def load_cookie_jar(path):
        '''
        A cookie jar is used to save user data, like cookies or localstorage.
        Given a path for a cookie jar, this function will load it into the
        WebView's environment.  This should be called before the WebView
        is constructed.

        The file does not need to exist - it will be created at the location
        specified if it does not exist.

        Args:
            path (str):  path to place cookie jar data
        '''
        session = WebKit.get_default_session()
        cookie_jar = SoupGNOME.CookieJarSqlite(
            filename=path,
            read_only=False)
        session.add_feature(cookie_jar)

    def register_uri_scheme(self, name, callback, user_data):
        '''
        Equivalent to calling :any:`WebKit2.WebContent.register_uri_scheme`
        for the webview's WebContext, but WebKit1 compatible.
        '''
        self._uri_schemes[name] = (callback, user_data)


    def __resource_request_starting_cb(self, webview, web_frame, web_resource,
                                      request, response):
        uri = web_resource.get_uri()
        for name, data in self._uri_schemes.iteritems():
            if uri.startswith(name + '://'):
                func, user_data = data
                func(_FakeWebKitURISchemeRequest(
                    name, webview, web_resource, request), user_data)
                return

    def get_session_state(self):
        back_forward_list = self.get_back_forward_list()
        items_list = self._items_history_as_list(back_forward_list)
        curr = back_forward_list.get_current_item()

        return ([item.get_uri() for item in items_list],
                items_list.index(curr))

    def restore_session_state(self, state):
        history, index = state

        back_forward_list = self.get_back_forward_list()
        back_forward_list.clear()
        for i, uri in enumerate(history):
            history_item = WebKit.WebHistoryItem.new_with_data(uri, '')
            back_forward_list.add_item(history_item)
            if i == index:
                self.go_to_back_forward_item(history_item)

    def _items_history_as_list(self, history):
        back_items = []
        for n in reversed(range(1, history.get_back_length() + 1)):
            item = history.get_nth_item(n * -1)
            back_items.append(item)

        current_item = [history.get_current_item()]

        forward_items = []
        for n in range(1, history.get_forward_length() + 1):
            item = history.get_nth_item(n)
            forward_items.append(item)

        all_items = back_items + current_item + forward_items
        return all_items

    def __load_status_changed_cb(self, *args):
        prop = LoadEvent.MAPPING.get(self.props.load_status)
        if prop is not None:
            self.load_changed_signal.emit(prop)

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

from gi.repository import WebKit2

from sugar3.graphics.webkit.shared import FilePicker


LoadEvent = WebKit2.LoadEvent


class WebView(WebKit2.WebView):

    needs_scrolled_window = False

    def do_run_filechooser(self, request):
        picker = FilePicker(self)
        chosen = picker.run()
        picker.destroy()

        if chosen:
            request.select_files([chosen])
        else:
            request.cancel()
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
        context = WebKit2.WebContext.get_default()
        cookie_manager = context.get_cookie_manager()
        cookie_manager.set_persistent_storage(
            path, WebKit2.CookiePersistentStorage.SQLITE)

    def register_uri_scheme(self, name, callback, user_data):
        '''
        Equivalent to calling :any:`WebKit2.WebContent.register_uri_scheme`
        for the webview's WebContext, but WebKit1 compatible.
        '''
        self.get_context().register_uri_scheme(name, callback, user_data)

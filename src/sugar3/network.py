# Copyright (C) 2006-2007 Red Hat, Inc.
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

import os
import threading
from six.moves import urllib
import fcntl
import tempfile

from gi.repository import GObject
from gi.repository import GLib
from six.moves import SimpleHTTPServer
from six.moves import socketserver


__authinfos = {}


def _add_authinfo(authinfo):
    __authinfos[threading.currentThread()] = authinfo


def get_authinfo():
    return __authinfos.get(threading.currentThread())


def _del_authinfo():
    del __authinfos[threading.currentThread()]


class GlibTCPServer(socketserver.TCPServer):
    """GlibTCPServer

    Integrate socket accept into glib mainloop.
    """

    allow_reuse_address = True
    request_queue_size = 20

    def __init__(self, server_address, RequestHandlerClass):
        socketserver.TCPServer.__init__(self, server_address,
                                        RequestHandlerClass)
        self.socket.setblocking(0)  # Set nonblocking

        # Watch the listener socket for data
        GLib.io_add_watch(self.socket, GLib.IO_IN, self._handle_accept)

    def _handle_accept(self, source, condition):
        """Process incoming data on the server's socket by doing an accept()
        via handle_request()."""
        if not (condition & GLib.IO_IN):
            return True
        self.handle_request()
        return True

    def close_request(self, request):
        """Called to clean up an individual request."""
        # let the request be closed by the request handler when its done
        pass

    def shutdown_request(self, request):
        """Called to shutdown and close an individual request."""
        # like close_request, let the request be closed by the request handler
        # when done
        pass


class ChunkedGlibHTTPRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    """RequestHandler class that integrates with Glib mainloop.  It writes
       the specified file to the client in chunks, returning control to the
       mainloop between chunks.
    """

    CHUNK_SIZE = 4096

    def __init__(self, request, client_address, server):
        self._file = None
        self._srcid = 0
        SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(
            self, request, client_address, server)

    def log_request(self, code='-', size='-'):
        pass

    def do_GET(self):
        """Serve a GET request."""
        self._file = self.send_head()
        if self._file:
            self._srcid = GLib.io_add_watch(self.wfile, GLib.IO_OUT |
                                            GLib.IO_ERR,
                                            self._send_next_chunk)
        else:
            self._cleanup()

    def _send_next_chunk(self, source, condition):
        if condition & GLib.IO_ERR:
            self._cleanup()
            return False
        if not (condition & GLib.IO_OUT):
            self._cleanup()
            return False
        data = self._file.read(self.CHUNK_SIZE)
        count = os.write(self.wfile.fileno(), data)
        if count != len(data) or len(data) != self.CHUNK_SIZE:
            self._cleanup()
            return False
        return True

    def _cleanup(self):
        if self._file:
            self._file.close()
            self._file = None
        if self._srcid > 0:
            GLib.source_remove(self._srcid)
            self._srcid = 0
        if not self.wfile.closed:
            self.wfile.flush()
        self.wfile.close()
        self.rfile.close()

    def finish(self):
        """Close the sockets when we're done, not before"""
        pass

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        ** [dcbw] modified to send Content-disposition filename too
        """
        path = self.translate_path(self.path)
        if not path or not os.path.exists(path):
            self.send_error(404, 'File not found')
            return None

        f = None
        if os.path.isdir(path):
            for index in 'index.html', 'index.htm':
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, 'File not found')
            return None
        self.send_response(200)
        self.send_header('Content-type', ctype)
        self.send_header('Content-Length', str(os.fstat(f.fileno())[6]))
        self.send_header('Content-Disposition', 'attachment; filename="%s"' %
                         os.path.basename(path))
        self.end_headers()
        return f


class GlibURLDownloader(GObject.GObject):
    """Grabs a URL in chunks, returning to the mainloop after each chunk"""

    __gsignals__ = {
        'finished': (GObject.SignalFlags.RUN_FIRST, None,
                     ([GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT])),
        'error': (GObject.SignalFlags.RUN_FIRST, None,
                  ([GObject.TYPE_PYOBJECT])),
        'progress': (GObject.SignalFlags.RUN_FIRST, None,
                     ([GObject.TYPE_PYOBJECT])),
    }

    CHUNK_SIZE = 4096

    def __init__(self, url, destdir=None):
        self._url = url
        if not destdir:
            destdir = tempfile.gettempdir()
        self._destdir = destdir
        self._srcid = 0
        self._fname = None
        self._outf = None
        self._suggested_fname = None
        self._info = None
        self._written = 0
        GObject.GObject.__init__(self)

    def start(self, destfile=None, destfd=None):
        self._info = urllib.request.urlopen(self._url)
        self._outf = None
        self._fname = None
        if destfd and not destfile:
            raise ValueError('Must provide destination file too when'
                             ' specifying file descriptor')
        if destfile:
            self._suggested_fname = os.path.basename(destfile)
            self._fname = os.path.abspath(os.path.expanduser(destfile))
            if destfd:
                # Use the user-supplied destination file descriptor
                self._outf = destfd
            else:
                self._outf = os.open(self._fname, os.O_RDWR |
                                     os.O_TRUNC | os.O_CREAT, 0o644)
        else:
            fname = self._get_filename_from_headers(self._info.headers)
            self._suggested_fname = fname
            garbage_, path = urllib.parse.splittype(self._url)
            garbage_, path = urllib.parse.splithost(path or "")
            path, garbage_ = urllib.parse.splitquery(path or "")
            path, garbage_ = urllib.parse.splitattr(path or "")
            suffix = os.path.splitext(path)[1]
            (self._outf, self._fname) = tempfile.mkstemp(suffix=suffix,
                                                         dir=self._destdir)

        fcntl.fcntl(self._info.fp.fileno(), fcntl.F_SETFD, os.O_NDELAY)
        self._srcid = GLib.io_add_watch(self._info.fp.fileno(),
                                        GLib.IO_IN | GLib.IO_ERR,
                                        self._read_next_chunk)

    def cancel(self):
        if self._srcid == 0:
            raise RuntimeError('Download already canceled or stopped')
        self.cleanup(remove=True)

    def _get_filename_from_headers(self, headers):
        if 'Content-Disposition' not in headers:
            return None

        ftag = 'filename='
        data = headers['Content-Disposition']
        fidx = data.find(ftag)
        if fidx < 0:
            return None
        fname = data[fidx + len(ftag):]
        if fname[0] == '"' or fname[0] == "'":
            fname = fname[1:]
        if fname[len(fname) - 1] == '"' or fname[len(fname) - 1] == "'":
            fname = fname[:len(fname) - 1]
        return fname

    def _read_next_chunk(self, source, condition):
        if condition & GLib.IO_ERR:
            self.cleanup(remove=True)
            self.emit('error', 'Error downloading file.')
            return False
        elif not (condition & GLib.IO_IN):
            # shouldn't get here, but...
            return True

        try:
            data = self._info.fp.read(self.CHUNK_SIZE)
            count = os.write(self._outf, data)
            self._written += len(data)

            # error writing data to file?
            if count < len(data):
                self.cleanup(remove=True)
                self.emit('error', 'Error writing to download file.')
                return False

            self.emit('progress', self._written)

            # done?
            if len(data) < self.CHUNK_SIZE:
                self.cleanup()
                self.emit('finished', self._fname, self._suggested_fname)
                return False
        except Exception as err:
            self.cleanup(remove=True)
            self.emit('error', 'Error downloading file: %r' % err)
            return False
        return True

    def cleanup(self, remove=False):
        if self._srcid > 0:
            GLib.source_remove(self._srcid)
            self._srcid = 0
        del self._info
        self._info = None
        os.close(self._outf)
        if remove:
            os.remove(self._fname)
        self._outf = None

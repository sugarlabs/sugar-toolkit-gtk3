# Copyright (C) 2013 Gonzalo Odiard
# Copyright (C) 2016 Sam Parkinson <sam@sam.today
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

from sugar3.graphics.objectchooser import ObjectChooser

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

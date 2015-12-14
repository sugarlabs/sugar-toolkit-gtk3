# Copyright (C) 2007, Red Hat, Inc.
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

import logging

from gi.repository import Gtk
from sugar3.presence.wrapper import CollabWrapper

'''
The collabtexteditor moudle provides a text editor widget 
which can be included in any activity and then multiple 
users can collaborate and edit together in the editor.
'''

class CollabTextEditor(Gtk.Box):
    '''
    A CollabTextEditor widget is a adjustable text editor which
    can be placed on an activity screen.
   
    The `changed` signal is usually emitted when the text in the
    editor is changed by a user.
    The `message` signal is usually emitted when another user makes
    changes in the text editor, so they are reflected in your editor.
    
    The widget can be embedded in a window which can be displayed.
    Example usage:
        editorinstance = CollabTextEditor(self)
        scrolled_window.add(editorinstance)
        scrolled_window.show()

    '''
    def __init__(self,activity,editor_id):
        Gtk.Box.__init__(self)
        self._id = editor_id
        self._collab = CollabWrapper(activity)
        self._collab.connect('message', self.__message_cb)
        self._collab.connect('buddy-joined', self.__buddy_joined_cb)
        self._collab.setup()
        self.textview = Gtk.TextView()
        self.textview.set_editable(True)
        self.textview.set_cursor_visible(True)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textbuffer = self.textview.get_buffer()
        self.textbuffer.connect('insert-text', self.__text_buffer_inserted_cb)
        self.textbuffer.connect('delete-range', self.__text_buffer_deleted_cb)
        self.textbuffer.set_text("")
        self.textview.show()
        self.pack_start(self.textview, expand=True, fill=True, padding=0)
        self.has_initialized = False
        self.show()

    '''
    The message callback is called whenever another user edits
    something in the text editor and the changes are reflected
    in the editor or when a new buddy joins and we send them the
    latest version of the text buffer.

    Args:
        buddy : another user who sent the message
        message : updates send over from other users
    '''
    def __message_cb(self, collab, buddy, message):
        action = message.get('action')
        if action == 'init_response' and self.has_initialized == False and message.get('res_id') == self._id:
            print 'response_for_init'
            self.has_initialized = True
            self.textbuffer.set_text(message.get('current_content'))
        if action == 'entry_inserted' and message.get('res_id') == self._id:
            self.textbuffer.insert(message.get('start_iter'),message.get('new_text'))
        if action == 'entry_deleted' and message.get('res_id') == self._id:
            self.textbuffer.delete(message.get('start_iter'),message.get('end_iter'))
   
    '''
    The buddy joined callback is called whenever another user joins
    this activity. We then send them the contents of the text buffer
    so that their text buffer is an identical copy.

    Args:
        buddy : another user who has joined the activity
    '''
    def __buddy_joined_cb(self, buddy):
        self._collab.post(dict(action='init_response', res_id = self._id, current_content=self.textbuffer.get_text(self.textbuffer.get_start_iter(),self.textbuffer.get_end_iter(),True)))

    '''
    The text buffer inserted callback is called whenever text is 
    inserted in the editor, so that other users get updated with 
    these changes.

    Args:
        textbuffer (:class:`Gtk.TextBuffer`): text storage widget
        start (:class:`Gtk.Iterator`): a pointer to the start position
    '''
    def __text_buffer_inserted_cb(self, textbuffer, start, text, length):
        if self.has_initialized == False:
            self.has_initialized = True
        logging.debug('Text inserted is %s' % (text))
        logging.debug('Text has been updated, %s' % (textbuffer.get_text(textbuffer.get_start_iter(), textbuffer.get_end_iter(), True)))
        self._collab.post(dict(action='entry_inserted', res_id = self._id, start_iter = start, new_text = text))

    '''
    The text buffer deleted callback is called whenever any text is 
    removed in the editor, so that other users get updated with 
    these changes.

    Args:
        textbuffer (:class:`Gtk.TextBuffer`): text storage widget
        start (:class:`Gtk.Iterator`): a pointer to the start position
        end (:class:`Gtk.Iterator`): a pointer to the end position
    '''
    def __text_buffer_deleted_cb(self,textbuffer,start,end):
        if self.has_initialized == False:
            self.has_initialized = True
        logging.debug('Text deleted is %s' % (textbuffer.get_text(start, end, True)))
        logging.debug('Text has been updated, %s' % (textbuffer.get_text(textbuffer.get_start_iter(), textbuffer.get_end_iter(), True)))
        self._collab.post(dict(action='entry_deleted', res_id = self._id, start_iter=start, end_iter=end))
        

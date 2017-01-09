# Copyright (C) 2015, Batchu Venkat Vishal
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
import time

from gi.repository import Gtk

try:
    from sugar3.presence.wrapper import CollabWrapper
    logging.error('USING SUGAR COLLAB WRAPPER')
except ImportError:
    from collabwrapper import CollabWrapper

'''
The collabtexteditor moudle provides a text editor widget 
which can be included in any activity and then multiple 
users can collaborate and edit together in the editor.
'''


class CollabTextEditor(Gtk.TextView):
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

    def __init__(self, activity, editor_id, collab):
        Gtk.TextView.__init__(self)
        self._id = editor_id
        self._callbacks_status = True
        collab.connect('message', self.__message_cb)
        collab.connect('buddy-joined', self.__buddy_joined_cb)
        self._collab = collab
        self.set_editable(True)
        self.set_cursor_visible(True)
        self.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textbuffer = self.get_buffer()
        self.textbuffer.connect('insert-text', self.__text_buffer_inserted_cb)
        self.textbuffer.connect('delete-range', self.__text_buffer_deleted_cb)
        self.textbuffer.set_text("")
        self.show()
        self.has_initialized = False

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
            self.has_initialized = True
            self._callbacks_status = False
            self.textbuffer.set_text(message.get('current_content'))
            self._callbacks_status = True
        if action == 'sync_editors' and message.get('res_id') == self._id:
            if self.has_initialized == False:
                self.has_initialized = True
            self._callbacks_status = False
            self.textbuffer.set_text(message.get('current_content'))
            self._callbacks_status = True
        if action == 'entry_inserted' and message.get('res_id') == self._id:
            start_iter=self.textbuffer.get_iter_at_line_offset(message.get('start_iter_line'),
                    message.get('start_iter_offset'))
            self._callbacks_status = False
            self.textbuffer.insert(start_iter, message.get('new_text'))
            self._callbacks_status = True
        if action == 'entry_deleted' and message.get('res_id') == self._id:
            start_iter=self.textbuffer.get_iter_at_line_offset(message.get('start_iter_line'),
                    message.get('start_iter_offset'))
            end_iter=self.textbuffer.get_iter_at_line_offset(message.get('end_iter_line'),
                    message.get('end_iter_offset'))
            self._callbacks_status = False
            self.textbuffer.delete(start_iter, end_iter)
            self._callbacks_status = True
    
    '''
    The buddy joined callback is called whenever another user joins
    this activity. The leader then send them the contents of the text 
    buffer so that their text buffer is an identical copy.
     
    Args:
         buddy : another user who has joined the activity
    '''
         
    def __buddy_joined_cb(self, sender, buddy):
        logging.debug("Buddy joined")
        if self._collab._leader == False:
            return
        if self.has_initialized == False:
            self.has_initialized = True
        time.sleep(0.5)
        self._collab.post(dict(action='init_response', res_id=self._id, 
            current_content=self.textbuffer.get_text(
            self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter(), True)))

    '''
    This will send a message to all your buddies to set their editors to 
    sync with the text specified as an argument.

    Args:
        text : Text to be set in all the editors
    '''
    def __set_text_synced(self, text):
        if self._callbacks_status == False:
            return
        if self.has_initialized == False:
            self.has_initialized = True
        self._callbacks_status = False
        self.textbuffer.set_text(text)
        self._callbacks_status = True
        self._collab.post(dict(action='sync_editors', res_id=self._id,
            current_content=text))

    '''
    The text buffer inserted callback is called whenever text is 
    inserted in the editor, so that other users get updated with 
    these changes.

    Args:
        textbuffer (:class:`Gtk.TextBuffer`): text storage widget
        start (:class:`Gtk.Iterator`): a pointer to the start position
    '''

    def __text_buffer_inserted_cb(self, textbuffer, start, text, length):
        if self._callbacks_status == False:
            return
        if self.has_initialized == False:
            self.has_initialized = True
        logging.debug('Text inserted is %s' % (text))
        logging.debug('Text has been updated, %s' % (textbuffer.get_text(
            textbuffer.get_start_iter(), textbuffer.get_end_iter(), True)))
        self._collab.post(dict(action='entry_inserted',
                               res_id=self._id, start_iter_offset=start.get_line_offset(), 
                               start_iter_line=start.get_line(), new_text=text))

    '''
    The text buffer deleted callback is called whenever any text is 
    removed in the editor, so that other users get updated with 
    these changes.

    Args:
        textbuffer (:class:`Gtk.TextBuffer`): text storage widget
        start (:class:`Gtk.Iterator`): a pointer to the start position
        end (:class:`Gtk.Iterator`): a pointer to the end position
    '''

    def __text_buffer_deleted_cb(self, textbuffer, start, end):
        if self._callbacks_status == False:
            return
        if self.has_initialized == False:
            self.has_initialized = True
        logging.debug('Text deleted is %s' %
                      (textbuffer.get_text(start, end, True)))
        logging.debug('Text has been updated, %s' % (textbuffer.get_text(
            textbuffer.get_start_iter(), textbuffer.get_end_iter(), True)))
        self._collab.post(dict(action='entry_deleted',
                               res_id=self._id, start_iter_offset=start.get_line_offset(), 
                               start_iter_line=start.get_line(),end_iter_offset=end.get_line_offset(), 
                               end_iter_line=end.get_line()))

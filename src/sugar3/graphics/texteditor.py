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
    def __init__(self,activity):
        Gtk.Box.__init__(self)
        self._collab = CollabWrapper(activity)
        self._collab.connect('message', self.__message_cb)
        self._collab.setup()
        self.textview = Gtk.TextView()
        self.textview.set_editable(True)
        self.textview.set_cursor_visible(True)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textbuffer = self.textview.get_buffer()
        self.textbuffer.connect('changed', self.__text_buffer_edited_cb)
        self.textbuffer.set_text("")
        self.textview.show()
        self.pack_start(self.textview, expand=True, fill=True, padding=0)
        self.show()

    '''
    The message callback is called whenever another user edits
    something in the text editor and the changes are reflected
    in the editor.

    Args:
        buddy : another user
	message : updates send over from other users
    '''
    def __message_cb(self, collab, buddy, message):
        action = message.get('action')
	if action == 'entry_changed':
	    self.textbuffer.set_text(message.get('new_text'))

    '''
    The text buffer edited callback is called whenever any changes
    are made in the editor, so that other users get updated with 
    these changes.

    Args:
        textbuffer (:class:`Gtk.TextBuffer`): text storage widget
    '''
    def __text_buffer_edited_cb(self,textbuffer):
	start_iter = textbuffer.get_start_iter()
	end_iter = textbuffer.get_end_iter()
	logging.debug('Text has been updated, %s' % (textbuffer.get_text(start_iter, end_iter, True)))
	self._collab.post(dict(action='entry_changed',new_text=textbuffer.get_text(start_iter, end_iter, True)))

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
	self.textbuffer.connect('insert-text', self.__text_buffer_inserted_cb)
	self.textbuffer.connect('delete-range', self.__text_buffer_deleted_cb)
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
	if action == 'entry_inserted':
	    self.textbuffer.insert(message.get('start_iter'),message.get('new_text'))
	if action == 'entry_deleted':
	    self.textbuffer.delete(message.get('start_iter'),message.get('end_iter'))

    '''
    The text buffer inserted callback is called whenever text is 
    inserted in the editor, so that other users get updated with 
    these changes.

    Args:
        textbuffer (:class:`Gtk.TextBuffer`): text storage widget
	start (:class:`Gtk.Iterator`): a pointer to the start position
    '''
    def __text_buffer_inserted_cb(self, textbuffer, start, text, length):
	logging.debug('Text inserted is %s' % (text))
	logging.debug('Text has been updated, %s' % (textbuffer.get_text(textbuffer.get_start_iter(), textbuffer.get_end_iter(), True)))
        self._collab.post(dict(action='entry_inserted', start_iter = start, new_text = text))

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
	logging.debug('Text deleted is %s' % (textbuffer.get_text(start, end, True)))
	logging.debug('Text has been updated, %s' % (textbuffer.get_text(textbuffer.get_start_iter(), textbuffer.get_end_iter(), True)))
        self._collab.post(dict(action='entry_deleted',start_iter=start,end_iter=end))

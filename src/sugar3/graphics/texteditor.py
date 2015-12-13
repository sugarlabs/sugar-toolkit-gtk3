import logging

from gi.repository import Gtk
from sugar3.presence.wrapper import CollabWrapper

class CollabTextEditor(Gtk.Box):
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

    def __message_cb(self, collab, buddy, message):
        action = message.get('action')
	if action == 'entry_changed':
	    self.textbuffer.set_text(message.get('new_text'))

    def __text_buffer_edited_cb(self,textbuffer):
	start_iter = textbuffer.get_start_iter()
	end_iter = textbuffer.get_end_iter()
	logging.debug('Text has been updated, %s' % (textbuffer.get_text(start_iter, end_iter, True)))
	self._collab.post(dict(action='entry_changed',new_text=textbuffer.get_text(start_iter, end_iter, True)))

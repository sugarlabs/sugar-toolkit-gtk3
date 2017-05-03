from gi.repository import Gtk

from sugar3.graphics.alert import Alert
from sugar3.graphics import style


class SaveAlert(Alert):
    """
    An alert popup to prompt the user to give a name to the journal
    entry.
    """
    __gtype_name__ = 'SaveAsAlert'

    def __init__(self, **kwargs):
        Alert.__init__(self, **kwargs)

        self.entry = Gtk.Entry()
        halign = Gtk.Alignment.new(0, 0, 1, 0)
        # FIXME: access to private member
        self._hbox.pack_start(halign, True, True, 0)
        halign.add(self.entry)

        halign = Gtk.Alignment.new(0, 0, 0, 0)
        # FIXME: access to private member
        self._buttons_box = Gtk.HButtonBox()
        self._buttons_box.set_layout(Gtk.ButtonBoxStyle.END)
        self._buttons_box.set_spacing(style.DEFAULT_SPACING)
        halign.add(self._buttons_box)
        self._hbox.pack_start(halign, False, False, 0)
        self.show_all()

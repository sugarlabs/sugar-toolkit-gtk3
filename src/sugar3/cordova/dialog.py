from gettext import gettext as _
import logging

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Wnck

from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton


class Dialog:
    def alert(self, args, parent, request):
        title = args[1]
        buttonLabel = args[2][0]
        message = args[0]
        show_dialog(parent, request, 'alert', message,
                    title, buttonLabel)

    def confirm(self, args, parent, request):
        message = args[0]
        title = args[1]
        buttonLabel = args[2]
        show_dialog(parent, request, 'confirm', message,
                    title, buttonLabel)

    def prompt(self, args, parent, request):
        message = args[0]
        title = args[1]
        buttonLabel = args[2]
        defaultText = args[3]
        show_dialog(parent, request, 'prompt', message,
                    title, buttonLabel, defaultText)


def dialog_response(dialog_box, response_id):
    dialog_box.destroy()


def show_dialog(parent, request, plugin_call, message,
                title, buttonLabel, defaultText=None):
    dialog = dialog_window(parent, request, plugin_call,
                           message, title, buttonLabel, defaultText)
    dialog.connect('response', dialog_response)
    dialog.show()


class dialog_window(Gtk.Window):

    __gtype_name__ = 'dialog_window'

    __gsignals__ = {
        'response': (GObject.SignalFlags.RUN_FIRST, None, ([int])),
    }

    def __init__(self, parent=None, request=[None], plugin_call="alert",
                 message="write a message text here", title="Alert",
                 buttonLabel="OK", defaultText=None):
        Gtk.Window.__init__(self)
        self.parent = parent
        self.request = request
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_border_width(style.LINE_WIDTH)
        self.set_has_resize_grip(False)
        self.add_events(Gdk.EventMask.VISIBILITY_NOTIFY_MASK)

        if self.parent._activity is None:
            logging.warning('Cordova dialog: No parent window specified')
        else:
            self.connect('realize', self.__realize_cb, self.parent._activity)
            screen = Wnck.Screen.get_default()
            screen.connect('window-closed', self.__window_closed_cb,
                           self.parent._activity)

        if plugin_call == 'alert':
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.add(vbox)
            vbox.show()

            title_box = TitleBox(title)
            title_box.close_button.connect('clicked',
                                           self.__close_button_clicked_cb)
            title_box.set_size_request(-1, style.GRID_CELL_SIZE)
            vbox.pack_start(title_box, False, True, 0)
            title_box.show()

            hbox = Gtk.HBox(spacing=50)
            vbox.add(hbox)

            label = Gtk.Label(message)
            hbox.pack_start(label, True, True, 0)

            button = Gtk.Button(buttonLabel)
            button.connect("clicked", self.__done_button_clicked_cb)
            vbox.pack_start(button, True, True, 0)

            self.show_all()

        elif plugin_call == 'confirm':
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.add(vbox)
            vbox.show()

            title_box = TitleBox(title)
            title_box.close_button.connect('clicked',
                                           self.__close_button_clicked_cb)
            title_box.set_size_request(-1, style.GRID_CELL_SIZE)
            vbox.pack_start(title_box, False, True, 0)
            title_box.show()

            hbox = Gtk.HBox(spacing=50)
            vbox.add(hbox)

            label = Gtk.Label(message)
            hbox.pack_start(label, True, True, 0)

            hbox2 = Gtk.HBox(spacing=50)
            vbox.add(hbox2)

            buttonLabel_number = 1

            button_labels = buttonLabel.split(",")

            # for button_label in buttonLabel:
            logging.error("button labels : ")
            logging.error(button_labels)
            for x in button_labels:
                button = Gtk.Button(x)
                button.connect("clicked",
                               self.__done_button_confirm_clicked_cb,
                               buttonLabel_number)
                hbox2.pack_start(button, True, True, 0)
                buttonLabel_number = buttonLabel_number + 1
                """
                button = Gtk.Button(button_label)
                button.connect("clicked",
                               self.__done_button_confirm_clicked_cb,
                               buttonLabel_number)
                hbox2.pack_start(button, True, True, 0)
                buttonLabel_number=buttonLabel_number+1
                """
            # self.width = 2*Gdk.Screen.width()/3
            # self.height = Gdk.Screen.height()/5 #- style.GRID_CELL_SIZE * 2
            # self.set_size_request(self.width, self.height)

            self.show_all()

        elif plugin_call == 'prompt':
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.add(vbox)
            vbox.show()

            title_box = TitleBox(title)
            title_box.close_button.connect('clicked',
                                           self.__close_button_clicked_cb)
            title_box.set_size_request(-1, style.GRID_CELL_SIZE)
            vbox.pack_start(title_box, False, True, 0)
            title_box.show()

            hbox = Gtk.HBox(spacing=50)
            vbox.add(hbox)

            label = Gtk.Label(message)
            hbox.pack_start(label, True, True, 0)

            self.entry = Gtk.Entry()
            self.entry.set_text(defaultText)
            vbox.pack_start(self.entry, True, True, 0)

            hbox2 = Gtk.HBox(spacing=50)
            vbox.add(hbox2)

            buttonLabel_number = 1

            logging.error("buttonLabel : %s", buttonLabel)
            # button_labels=buttonLabel.split(",")
            # for button_label in buttonLabel:
            # logging.error("button labels : ")
            # logging.error(button_labels)
            for x in buttonLabel:
                button = Gtk.Button(x)
                button.connect("clicked",
                               self.__done_button_prompt_clicked_cb,
                               buttonLabel_number)
                hbox2.pack_start(button, True, True, 0)
                buttonLabel_number = buttonLabel_number + 1
                """
                button = Gtk.Button(button_label)
                button.connect("clicked",
                               self.__done_button_confirm_clicked_cb,
                               buttonLabel_number)
                hbox2.pack_start(button, True, True, 0)
                buttonLabel_number=buttonLabel_number+1
                """
            # self.width = 2*Gdk.Screen.width()/3
            # self.height = Gdk.Screen.height()/5 #- style.GRID_CELL_SIZE * 2
            # self.set_size_request(self.width, self.height)

            self.show_all()

    def __realize_cb(self, chooser, parent):
        logging.error("hello")
        self.get_window().set_transient_for(parent)

    def __window_closed_cb(self, screen, window, parent):
        if window.get_xid() == parent.get_xid():
            self.destroy()

    def __close_button_clicked_cb(self, button):
        logging.error("alert close button pressed - no response")
        # self.emit('response', Gtk.ResponseType.DELETE_EVENT)

    def __done_button_clicked_cb(self, button):
        self.parent._client.send_result(self.request, [None])
        self.emit('response', Gtk.ResponseType.DELETE_EVENT)

    def __done_button_confirm_clicked_cb(self, button, buttonLabel_number):
        logging.error("button pressed : %s", button.get_name())
        logging.error("number of the button pressed : %s", buttonLabel_number)
        self.parent._client.send_result(self.request, buttonLabel_number)
        self.emit('response', Gtk.ResponseType.DELETE_EVENT)

    def __done_button_prompt_clicked_cb(self, button, buttonLabel_number):
        logging.error("button pressed : %s", button.get_name())
        logging.error("number of the button pressed : %s", buttonLabel_number)
        result = {"input1": self.entry.get_text(),
                  "buttonIndex": buttonLabel_number}
        self.parent._client.send_result(self.request, result)
        self.emit('response', Gtk.ResponseType.DELETE_EVENT)


class TitleBox(Gtk.Toolbar):

    def __init__(self, title_text):
        Gtk.Toolbar.__init__(self)

        label = Gtk.Label()
        title = _(title_text)

        label.set_markup('<b>%s</b>' % title)
        label.set_alignment(0, 0.5)
        self._add_widget(label, expand=True)

        self.close_button = ToolButton(icon_name='dialog-cancel')
        """
        self.close_button.set_tooltip(_('Close'))
        """
        self.insert(self.close_button, -1)
        self.close_button.show()

    def _add_widget(self, widget, expand=False):
        tool_item = Gtk.ToolItem()
        tool_item.set_expand(expand)

        tool_item.add(widget)
        widget.show()

        self.insert(tool_item, -1)
        tool_item.show()

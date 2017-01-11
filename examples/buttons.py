from gi.repository import Gtk

import common


test = common.Test()
test.show()

box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
test.pack_start(box, True, True, 0)
box.show()

# test Gtk.SpinButton:

adj = Gtk.Adjustment(0, 0, 10, 1, 32, 0)
spin = Gtk.SpinButton()
spin.set_adjustment(adj)
box.pack_start(spin, False, False, 1)
spin.show()

# test Gtk.RadioButton:

radio_1 = Gtk.RadioButton.new_with_label_from_widget(None, 'Radio 1')
box.pack_start(radio_1, False, False, 1)
radio_1.show()
radio_2 = Gtk.RadioButton.new_with_label_from_widget(radio_1, 'Radio 2')
box.pack_start(radio_2, False, False, 1)
radio_2.show()
radio_3 = Gtk.RadioButton.new_with_label_from_widget(radio_1, 'Radio 3')
box.pack_start(radio_3, False, False, 1)
radio_3.show()

# test Gtk.CheckButton:

check_1 = Gtk.CheckButton('Check 1')
box.pack_start(check_1, False, False, 1)
check_1.show()

check_2 = Gtk.CheckButton('Check 2')
box.pack_start(check_2, False, False, 1)
check_2.show()

# test Gtk.Button:

button = Gtk.Button('Button')
box.pack_start(button, False, False, 1)
button.show()

# test Gtk.Button insensitive:

insensitive_button = Gtk.Button('Insensitive Button')
box.pack_start(insensitive_button, False, False, 1)
insensitive_button.props.sensitive = False
insensitive_button.show()

# test Gtk.ToggleButton:

toggle_button = Gtk.ToggleButton('ToggleButton')
box.pack_start(toggle_button, False, False, 1)
toggle_button.show()


if __name__ == '__main__':
    common.main(test)

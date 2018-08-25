from sugar3.graphics.popwindow import PopWindow

import common
test = common.Test()


def popwindow_closed(widget):
    print("Popwindow closed")


c = PopWindow()
c.connect('destroy', popwindow_closed)
c.show_all()  # Press `escape` key or click on the close_button to close the popwindow

if __name__ == '__main__':
    common.main(test)

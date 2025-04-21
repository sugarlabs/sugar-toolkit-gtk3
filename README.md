# Sugar Toolkit GTK3

Sugar Toolkit provides services and a set of GTK+ widgets to build activities and other Sugar components on Linux-based computers. This toolkit is designed to work seamlessly with the Sugar Learning Environment, enabling developers to create educational applications with intuitive, child-friendly interfaces.

---

## Features
- **Pre-built GTK+ Widgets**: Simplify UI design for activities.
- **Integration with Sugar Environment**: Access system services, datastore, and collaboration tools.
- **Lightweight and Modular**: Build standalone activities or integrate into the Sugar desktop.

For more information, visit:
- [Sugar Labs Official Website](https://www.sugarlabs.org/)
- [Sugar Labs Wiki](https://wiki.sugarlabs.org/)

---

## Installation

### Debian/Ubuntu
Sugar Toolkit GTK3 is automatically installed with [Sugar desktop](https://github.com/sugarlabs/sugar).
To install Sugar Toolkit alone without Sugar desktop:

```bash
sudo apt install python3-sugar3
```

### Fedora
Similar to Debian/Ubuntu, it is included with the [Sugar desktop](https://github.com/sugarlabs/sugar).
To install Sugar Toolkit alone without Sugar desktop:

```bash
sudo dnf install sugar-toolkit-gtk3
```

---

## Building from Source
Sugar Toolkit GTK3 follows the [GNU Coding Standards](https://www.gnu.org/prep/standards/).

### Prerequisites
Ensure the following dependencies are installed:
- `sugar-artwork`
- `sugar-datastore`
- `GTK+ 3`

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/sugarlabs/sugar-toolkit-gtk3.git
   cd sugar-toolkit-gtk3
   ```
2. Run the configuration script:
   ```bash
   ./autogen.sh
   ```
3. Build and install:
   ```bash
   make
   sudo make install
   ```

---

## Usage

Sugar Toolkit GTK3 is primarily used to create Sugar activities. Below is a simple example of a "Hello World" activity:

### File Structure
```
hello-world/
├── activity/
│   ├── activity.info
│   └── icon.svg
├── hello-world.py
└── setup.py
```

### Code Example: `hello-world.py`
```python
from gi.repository import Gtk
from sugar3.activity.activity import Activity

class HelloWorldActivity(Activity):
    def __init__(self, handle):
        Activity.__init__(self, handle)

        label = Gtk.Label(label="Hello, Sugar!")
        self.set_canvas(label)
        self.show_all()
```

### Running the Activity
1. Bundle the activity:
   ```bash
   python3 setup.py dist_xo
   ```
2. Copy the `.xo` file to the Sugar environment's Activities folder (usually `~/Activities`).
3. Restart Sugar and launch your activity!

---

## Contributing

We welcome contributions from the community! Follow these steps to get started:

1. **Fork the Repository**:
   ```bash
   git clone https://github.com/sugarlabs/sugar-toolkit-gtk3.git
   ```
2. **Create a Feature Branch**:
   ```bash
   git checkout -b feature-name
   ```
3. **Make Your Changes** and **Commit**:
   ```bash
   git commit -m "Description of changes"
   ```
4. **Push Your Branch**:
   ```bash
   git push origin feature-name
   ```
5. **Submit a Pull Request**: Include a clear description of your changes and why they are beneficial.

Use the above process to setup and create activities, and contribute to the Sugar Labs community.

---

## Community and Support

If you have questions or need help, you can:
- Join the [Sugar Labs Mailing List](https://lists.sugarlabs.org/)
- Join the chat [Element Chat](https://app.element.io/#/room/#sugar:matrix.org)



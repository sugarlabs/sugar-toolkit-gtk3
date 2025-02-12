# Setting Up a Virtual Environment and Running from Source

## Creating a Virtual Environment

1. Open a terminal.
2. Navigate to your project directory:
3. Create a virtual environment:
    ```sh
    python3 -m venv venv
    ```
4. Activate the virtual environment:
    - On Linux/macOS:
        ```sh
        source venv/bin/activate
        ```
    - On Windows:
        ```sh
        .\venv\Scripts\activate
        ```

## Installing Dependencies

1. Ensure you have `pip` installed. If not, install it:
    ```sh
    python3 -m ensurepip --upgrade
    ```

## Setting the PYTHONPATH

1. Set the `PYTHONPATH` to include the `src` directory:
    ```sh
    export PYTHONPATH=$(pwd)/src
    ```

## Running from Source

1. Ensure the virtual environment is activated.
2. Run the application:
    ```sh
    python path/to/your/main_script.py
    ```

## Deactivating the Virtual Environment

1. When you are done, deactivate the virtual environment:
    ```sh
    deactivate
    ```




## Porting to GTK 4.0

### Changes Made

1. **Updated `gi.require_version` Calls:**
    - Changed `'Gtk', '3.0'` and `'Gdk', '3.0'` to `'Gtk', '4.0'` and `'Gdk', '4.0'` respectively.

2. **Refactored Deprecated GTK 3.0 APIs:**
    - Replaced `Gtk.VBox` and `Gtk.HBox` with `Gtk.Box` using orientation.
    - Removed `Gtk.EventBox` and implemented event controllers.

3. **Refactored Icon and EventIcon Classes:**
    - Updated the `Icon` and `EventIcon` classes to be compatible with GTK 4.0.

4. **Refactored Alert and TimeoutIcon Classes:**
    - Modified the `Alert` and `TimeoutIcon` classes to use `Gtk.Box` and updated them to GTK 4.0.

5. **Updated Version Requirements:**
    - Changed the GDK and GTK version requirements to 4.0 in the project configuration files.

6. **Refactored Activity Class Initialization:**
    - Updated the initialization process of the `Activity` class to be compatible with GTK 4.0.


## Installing Build Dependencies
### On Debian/Ubuntu:
```bash
sudo apt-get install \
    build-essential \
    python3-dev \
    libgtk-4-dev \
    libgdk-pixbuf-2.0-dev \
    gobject-introspection \
    libgirepository1.0-dev \
    gir1.2-gtk-4.0 \
    python3-gi \
    libx11-dev \
    libxi-dev \
    libxext-dev \
    libxrandr-dev \
    libxrender-dev \
    libxtst-dev \
    autoconf \
    automake \
    libtool \
    libasound2-dev \
    librsvg2-dev \
```

- If using Debian 11 (Bullseye):
- Add backports to /etc/apt/sources.list:
```bash
sudo echo "deb http://deb.debian.org/debian bullseye-backports main" >> /etc/apt/sources.list
```
-Update and install from backports:
```
sudo apt update
sudo apt -t bullseye-backports install libgtk-4-dev
```

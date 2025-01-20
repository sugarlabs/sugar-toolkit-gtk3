# Setting Up a Virtual Environment and Running from Source

## Creating a Virtual Environment

1. Open a terminal.
2. Navigate to your project directory:
    ```sh
    cd /home/mostlyk/Documents/GitHub/sugar-toolkit-gtk3
    ```
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
2. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
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

## Additional Notes

- Ensure you have Python 3.6 or higher installed.
- Update your `requirements.txt` file with any new dependencies using:
    ```sh
    pip freeze > requirements.txt
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


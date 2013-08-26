/*
 * Copyright (C) 2012, Daniel Narvaez
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#include <string.h>
#include <X11/Xatom.h>
#include <gdk/gdkx.h>

#include "sugar-wm.h"

#define MAX_PROPERTY_LEN 1024

static char *
get_property(Window window, const char *name)
{
    Display *display;
    Atom property;
    Atom actual_type;
    int actual_format;
    unsigned long n_items;
    unsigned long bytes_after;
    unsigned char *data;

    display = gdk_x11_get_default_xdisplay();
    property = XInternAtom(display, name, False);

    if (XGetWindowProperty(display, window, property, 0, MAX_PROPERTY_LEN,
                           False, XA_STRING, &actual_type, &actual_format,
                           &n_items, &bytes_after, &data) != Success) {
        return NULL;
    }

    return (char *)data;
}

static void
set_property(Window window, const char *name, const char *value)
{
    Display *display;
    Atom property;

    display = gdk_x11_get_default_xdisplay();
    property = XInternAtom(display, name, False);

    XChangeProperty (display, window, property, XA_STRING, 8, PropModeReplace,
                     (unsigned char *)value, strlen(value));
}

char *
sugar_wm_get_activity_id(Window window)
{
    return get_property(window, "_SUGAR_ACTIVITY_ID");
}

char *
sugar_wm_get_bundle_id(Window window)
{
    return get_property(window, "_SUGAR_BUNDLE_ID");
}

void
sugar_wm_set_activity_id(Window window, const char *activity_id)
{
    set_property(window, "_SUGAR_ACTIVITY_ID", activity_id);
}

void
sugar_wm_set_bundle_id(Window window, const char *bundle_id)
{
    set_property(window, "_SUGAR_BUNDLE_ID", bundle_id);
}

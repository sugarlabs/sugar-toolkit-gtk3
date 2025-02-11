/*
 * Copyright (C) 2006-2007, Red Hat, Inc.
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

#include <X11/X.h>
#include <X11/Xlib.h>
#include <X11/extensions/XInput2.h>
#include <gdk/gdk.h>
#include <gdk/x11/gdkx.h>

#include "sugar-key-grabber.h"
#include "eggaccelerators.h"
#include "sugar-marshal.h"

/* we exclude shift, GDK_CONTROL_MASK and GDK_MOD1_MASK since we know what
these modifiers mean
these are the mods whose combinations are bound by the keygrabbing code */
#define IGNORED_MODS (0x2000 /*Xkb modifier*/ | GDK_LOCK_MASK  | \
        GDK_ALT_MASK | GDK_SUPER_MASK | GDK_HYPER_MASK | GDK_META_MASK)

/* these are the ones we actually use for global keys, we always only check
* for these set */
#define USED_MODS (GDK_SHIFT_MASK | GDK_CONTROL_MASK | GDK_ALT_MASK)

enum {
    KEY_PRESSED,
    KEY_RELEASED,
    N_SIGNALS
};

typedef struct {
    char *key;
    guint keysym;
    guint state;
    guint keycode;
} Key;

G_DEFINE_TYPE(SugarKeyGrabber, sugar_key_grabber, G_TYPE_OBJECT)

static guint signals[N_SIGNALS];

static void
free_key_info(Key *key_info)
{
    g_free(key_info->key);
    g_free(key_info);
}

static void
sugar_key_grabber_dispose(GObject *object)
{
    SugarKeyGrabber *grabber = SUGAR_KEY_GRABBER(object);

    if (grabber->keys) {
        g_list_foreach(grabber->keys, (GFunc)free_key_info, NULL);
        g_list_free(grabber->keys);
        grabber->keys = NULL;
    }

    G_OBJECT_CLASS(sugar_key_grabber_parent_class)->dispose(object);
}

static void
sugar_key_grabber_class_init(SugarKeyGrabberClass *grabber_class)
{
    GObjectClass *g_object_class = G_OBJECT_CLASS(grabber_class);

    g_object_class->dispose = sugar_key_grabber_dispose;

    signals[KEY_PRESSED] = g_signal_new("key-pressed",
                    G_TYPE_FROM_CLASS(grabber_class),
                    G_SIGNAL_RUN_LAST | G_SIGNAL_ACTION,
                    G_STRUCT_OFFSET(SugarKeyGrabberClass, key_pressed),
                    NULL, NULL,
                    sugar_marshal_BOOLEAN__UINT_UINT_UINT,
                    G_TYPE_BOOLEAN, 3,
                    G_TYPE_UINT,
                    G_TYPE_UINT,
                    G_TYPE_UINT);

    signals[KEY_RELEASED] = g_signal_new("key-released",
                    G_TYPE_FROM_CLASS(grabber_class),
                    G_SIGNAL_RUN_LAST | G_SIGNAL_ACTION,
                    G_STRUCT_OFFSET(SugarKeyGrabberClass, key_released),
                    NULL, NULL,
                    sugar_marshal_BOOLEAN__UINT_UINT_UINT,
                    G_TYPE_BOOLEAN, 3,
                    G_TYPE_UINT,
                    G_TYPE_UINT,
                    G_TYPE_UINT);
}

char *
sugar_key_grabber_get_key(SugarKeyGrabber *grabber, guint keycode, guint state)
{
    GList *l;

    for (l = grabber->keys; l != NULL; l = l->next) {
        Key *keyinfo = (Key *)l->data;
        if ((keyinfo->keycode == keycode) &&
            ((state & USED_MODS) == keyinfo->state)) {
            return g_strdup(keyinfo->key);
        }
    }

    return NULL;
}

static gboolean
key_event_handler(GtkEventControllerKey *controller,
                 guint keyval,
                 guint keycode,
                 GdkModifierType state,
                 gpointer user_data)
{
    SugarKeyGrabber *grabber = SUGAR_KEY_GRABBER(user_data);
    gboolean handled = FALSE;
    guint32 time = g_get_monotonic_time() / 1000; // Convert to milliseconds

    // Determine if this is a press or release
    GdkEvent *event = gtk_event_controller_get_current_event(GTK_EVENT_CONTROLLER(controller));
    if (gdk_event_get_event_type(event) == GDK_KEY_PRESS) {
        g_signal_emit(grabber, signals[KEY_PRESSED], 0,
                     keycode, state, time, &handled);
    } else if (gdk_event_get_event_type(event) == GDK_KEY_RELEASE) {
        g_signal_emit(grabber, signals[KEY_RELEASED], 0,
                     keycode, state, time, &handled);
    }

    return handled;
}

static void
sugar_key_grabber_init(SugarKeyGrabber *grabber)
{
    GdkDisplay *display;
    
    display = gdk_display_get_default();
    if (!display)
        return;

    // Create a fullscreen window to act as root
    GtkWindow *window = GTK_WINDOW(gtk_window_new());
    if (window) {
        gtk_window_fullscreen(window);
        gtk_window_set_decorated(window, FALSE);
        gtk_widget_set_visible(GTK_WIDGET(window), TRUE);
        
        // Add key event controller
        GtkEventController *key_controller = gtk_event_controller_key_new();
        g_signal_connect(key_controller, "key-pressed",
                        G_CALLBACK(key_event_handler), grabber);
        g_signal_connect(key_controller, "key-released",
                        G_CALLBACK(key_event_handler), grabber);
        gtk_widget_add_controller(GTK_WIDGET(window), key_controller);
        
        grabber->root = gtk_native_get_surface(GTK_NATIVE(window));
    }

    grabber->keys = NULL;
}

static void
grab_key_real(Key *key, GdkSurface *root, gboolean grab, int result)
{
    Display *display = GDK_DISPLAY_XDISPLAY(gdk_display_get_default());
    if (grab)
        XGrabKey(display, key->keycode, (result | key->state),
                gdk_x11_surface_get_xid(root), True,
                GrabModeAsync, GrabModeAsync);
    else
        XUngrabKey(display, key->keycode, (result | key->state),
                  gdk_x11_surface_get_xid(root));
}

#define N_BITS 32
static void
grab_key(SugarKeyGrabber *grabber, Key *key, gboolean grab)
{
    int indexes[N_BITS];/*indexes of bits we need to flip*/
    int i, bit, bits_set_cnt;
    int uppervalue;
    guint mask_to_traverse = IGNORED_MODS & ~key->state & GDK_MODIFIER_MASK;

    bit = 0;
    for (i = 0; i < N_BITS; i++) {
        if (mask_to_traverse & (1<<i))
            indexes[bit++]=i;
    }

    bits_set_cnt = bit;

    uppervalue = 1<<bits_set_cnt;
    for (i = 0; i < uppervalue; i++) {
        int j, result = 0;

        for (j = 0; j < bits_set_cnt; j++) {
            if (i & (1<<j))
                result |= (1<<indexes[j]);
        }

        grab_key_real(key, grabber->root, grab, result);
    }
}

void
sugar_key_grabber_grab_keys(SugarKeyGrabber *grabber,
                           const gchar *keys[],
                           gint n_elements)
{
    gint i;
    Key *keyinfo = NULL;
    gint min_keycodes, max_keycodes;
    GdkDisplay *display = gdk_display_get_default();

    XDisplayKeycodes(GDK_DISPLAY_XDISPLAY(display),
                    &min_keycodes, &max_keycodes);

    for (i = 0; i < n_elements; i++) {
        keyinfo = g_new0(Key, 1);
        keyinfo->key = g_strdup(keys[i]);

        if (!egg_accelerator_parse_virtual(keys[i], &keyinfo->keysym,
                                         &keyinfo->keycode,
                                         &keyinfo->state)) {
            g_warning("Invalid key specified: %s", keys[i]);
            free_key_info(keyinfo);
            continue;
        }

        if (keyinfo->keycode < min_keycodes ||
            keyinfo->keycode > max_keycodes) {
            g_warning("Keycode out of bounds: %d for key %s",
                     keyinfo->keycode, keys[i]);
            free_key_info(keyinfo);
            continue;
        }

        gdk_x11_display_error_trap_push(display);
        grab_key(grabber, keyinfo, TRUE);
        gdk_display_sync(display);
        
        gint error_code = gdk_x11_display_error_trap_pop(display);
        
        if (!error_code)
            grabber->keys = g_list_append(grabber->keys, keyinfo);
        else if (error_code == BadAccess)
            g_warning("Grab failed, another application may already have access to key '%s'",
                     keys[i]);
        else if (error_code == BadValue)
            g_warning("Grab failed, invalid key %s specified. keysym: %u keycode: %u state: %u",
                     keys[i], keyinfo->keysym, keyinfo->keycode, keyinfo->state);
        else
            g_warning("Grab failed for key '%s' for unknown reason '%d'",
                     keys[i], error_code);
    }
}

gboolean
sugar_key_grabber_is_modifier(SugarKeyGrabber *grabber, guint keycode, guint mask)
{
    Display *xdisplay;
    XModifierKeymap *modmap;
    gint start, end, i, mod_index;
    gboolean is_modifier = FALSE;

    xdisplay = GDK_DISPLAY_XDISPLAY(gdk_display_get_default());

    modmap = XGetModifierMapping(xdisplay);

    if (mask != -1) {
        mod_index = 0;
        mask = mask >> 1;
        while (mask != 0) {
            mask = mask >> 1;
            mod_index += 1;
        }
        start = mod_index * modmap->max_keypermod;
        end = (mod_index + 1) * modmap->max_keypermod;
    } else {
        start = 0;
        end = 8 * modmap->max_keypermod;
    }

    for (i = start; i < end; i++) {
        if (keycode == modmap->modifiermap[i]) {
            is_modifier = TRUE;
            break;
        }
    }

    XFreeModifiermap(modmap);

    return is_modifier;
}

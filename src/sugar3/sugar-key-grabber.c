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
#include <gdk/gdkx.h>

#include "sugar-key-grabber.h"
#include "eggaccelerators.h"
#include "sugar-marshal.h"

/* we exclude shift, GDK_CONTROL_MASK and GDK_MOD1_MASK since we know what
   these modifiers mean
   these are the mods whose combinations are bound by the keygrabbing code */
#define IGNORED_MODS (0x2000 /*Xkb modifier*/ | GDK_LOCK_MASK  | \
        GDK_MOD2_MASK | GDK_MOD3_MASK | GDK_MOD4_MASK | GDK_MOD5_MASK)
/* these are the ones we actually use for global keys, we always only check
 * for these set */
#define USED_MODS (GDK_SHIFT_MASK | GDK_CONTROL_MASK | GDK_MOD1_MASK)

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
sugar_key_grabber_dispose (GObject *object)
{
	SugarKeyGrabber *grabber = SUGAR_KEY_GRABBER(object);

	if (grabber->keys) {
		g_list_foreach(grabber->keys, (GFunc)free_key_info, NULL);
		g_list_free(grabber->keys);
		grabber->keys = NULL;
	}
}

static void
sugar_key_grabber_class_init(SugarKeyGrabberClass *grabber_class)
{
	GObjectClass *g_object_class = G_OBJECT_CLASS (grabber_class);

	g_object_class->dispose = sugar_key_grabber_dispose;

	signals[KEY_PRESSED] = g_signal_new ("key-pressed",
                         G_TYPE_FROM_CLASS (grabber_class),
                         G_SIGNAL_RUN_LAST | G_SIGNAL_ACTION,
                         G_STRUCT_OFFSET (SugarKeyGrabberClass, key_pressed),
                         NULL, NULL,
                         sugar_marshal_BOOLEAN__UINT_UINT_UINT,
                         G_TYPE_BOOLEAN, 3,
                         G_TYPE_UINT,
                         G_TYPE_UINT,
                         G_TYPE_UINT);
	signals[KEY_RELEASED] = g_signal_new ("key-released",
                         G_TYPE_FROM_CLASS (grabber_class),
                         G_SIGNAL_RUN_LAST | G_SIGNAL_ACTION,
                         G_STRUCT_OFFSET (SugarKeyGrabberClass, key_released),
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

static GdkFilterReturn
filter_events(GdkXEvent *xevent, GdkEvent *event, gpointer data)
{
	SugarKeyGrabber *grabber = (SugarKeyGrabber *)data;
	XEvent *xev = (XEvent *)xevent;

	if (xev->type == KeyRelease) {
		int return_value;
		g_signal_emit (grabber, signals[KEY_RELEASED], 0, xev->xkey.keycode,
					   xev->xkey.state, xev->xkey.time, &return_value);
		if(return_value)
			return GDK_FILTER_REMOVE;
	}

	if (xev->type == KeyPress) {
		int return_value;
		g_signal_emit (grabber, signals[KEY_PRESSED], 0, xev->xkey.keycode,
					   xev->xkey.state, xev->xkey.time, &return_value);
		if(return_value)
			return GDK_FILTER_REMOVE;
	}

	if (xev->type == GenericEvent) {
		XIDeviceEvent *ev;
		int return_value = FALSE;

		ev = (XIDeviceEvent *) ((XGenericEventCookie *) xev)->data;

		if (ev->evtype == XI_KeyPress) {
			g_signal_emit (grabber, signals[KEY_PRESSED], 0,
				       ev->detail, ev->mods.effective, ev->time, &return_value);
		} else if (ev->evtype == XI_KeyRelease) {
			g_signal_emit (grabber, signals[KEY_RELEASED], 0,
				       ev->detail, ev->mods.effective, ev->time, &return_value);
		}

		if (return_value)
			return GDK_FILTER_REMOVE;
	}


	return GDK_FILTER_CONTINUE;
}

static void
sugar_key_grabber_init(SugarKeyGrabber *grabber)
{
	GdkScreen *screen;

	screen = gdk_screen_get_default();
	grabber->root = gdk_screen_get_root_window(screen);
	grabber->keys = NULL;

	gdk_window_add_filter(grabber->root, filter_events, grabber);
}

/* grab_key and grab_key_real are from
 * gnome-control-center/gnome-settings-daemon/gnome-settings-multimedia-keys.c
 */

static void
grab_key_real (Key *key, GdkWindow *root, gboolean grab, int result)
{
        Display *display = GDK_DISPLAY_XDISPLAY(gdk_display_get_default ());
        if (grab)
                XGrabKey (display, key->keycode, (result | key->state),
                                GDK_WINDOW_XID (root), True, GrabModeAsync, GrabModeAsync);
        else
                XUngrabKey(display, key->keycode, (result | key->state),
                                GDK_WINDOW_XID (root));
}

#define N_BITS 32
static void
grab_key (SugarKeyGrabber *grabber, Key *key, gboolean grab)
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

                grab_key_real (key, grabber->root, grab, result);
        }
}

/**
 * sugar_key_grabber_grab_keys:
 * @grabber: a #SugarKeyGrabber
 * @keys: (array length=n_elements) (element-type utf8): array of
 *     keys the grabber will listen to
 * @n_elements: number of elements in @keys.
 *
 * Pass to the key grabber the keys it should listen to.
 **/
void
sugar_key_grabber_grab_keys(SugarKeyGrabber *grabber,
			    const gchar  *keys[],
			    gint          n_elements)
{
    gint i;
    const char *key;
    Key *keyinfo = NULL;
    gint min_keycodes, max_keycodes;

    XDisplayKeycodes(GDK_DISPLAY_XDISPLAY(gdk_display_get_default()),
                     &min_keycodes, &max_keycodes);

    for (i = 0; i < n_elements; i++){
	keyinfo = g_new0 (Key, 1);
	keyinfo->key = g_strdup(keys[i]);

        if (!egg_accelerator_parse_virtual (keys[i], &keyinfo->keysym,
                                            &keyinfo->keycode,
                                            &keyinfo->state)) {
            g_warning ("Invalid key specified: %s", keys[i]);
            continue;
        }

        if (keyinfo->keycode < min_keycodes || keyinfo->keycode > max_keycodes) {
            g_warning ("Keycode out of bounds: %d for key %s", keyinfo->keycode, keys[i]);
            continue;
        }

        gdk_error_trap_push();

        grab_key(grabber, keyinfo, TRUE);

        gdk_flush();
        gint error_code = gdk_error_trap_pop ();
        if(!error_code)
            grabber->keys = g_list_append(grabber->keys, keyinfo);
        else if(error_code == BadAccess)
            g_warning ("Grab failed, another application may already have access to key '%s'", keys[i]);
        else if(error_code == BadValue)
            g_warning ("Grab failed, invalid key %s specified. keysym: %u keycode: %u state: %u",
                       keys[i], keyinfo->keysym, keyinfo->keycode, keyinfo->state);
        else
            g_warning ("Grab failed for key '%s' for unknown reason '%d'", keys[i], error_code);

    }
}

gboolean
sugar_key_grabber_is_modifier(SugarKeyGrabber *grabber, guint keycode, guint mask)
{
	Display *xdisplay;
	XModifierKeymap *modmap;
	gint start, end, i, mod_index;
	gboolean is_modifier = FALSE;

	xdisplay = GDK_DISPLAY_XDISPLAY(gdk_display_get_default ());

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

	XFreeModifiermap (modmap);

	return is_modifier;
}

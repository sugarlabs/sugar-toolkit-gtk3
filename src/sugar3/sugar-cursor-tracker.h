/*
 * Copyright (C) 2012 One laptop per child
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
 *
 * Author: Simon Schampijer  <simon@laptop.org>
 */

#ifndef __SUGAR_CURSOR_TRACKER_H__
#define __SUGAR_CURSOR_TRACKER_H__

#include <gtk/gtk.h>

G_BEGIN_DECLS

typedef struct _SugarCursorTracker SugarCursorTracker;
typedef struct _SugarCursorTrackerClass SugarCursorTrackerClass;

#define SUGAR_TYPE_CURSOR_TRACKER (sugar_cursor_tracker_get_type())
G_DECLARE_DERIVABLE_TYPE(SugarCursorTracker, sugar_cursor_tracker, SUGAR, CURSOR_TRACKER, GObject)

struct _SugarCursorTrackerClass {
    GObjectClass parent_class;
};

/* Private structure */
typedef struct {
    GdkSurface *root_surface;
    gboolean cursor_shown;
} SugarCursorTrackerPrivate;

SugarCursorTracker *sugar_cursor_tracker_new(void);

G_END_DECLS

#endif /* __SUGAR_CURSOR_TRACKER_H__ */

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
#include "event-controller/sugar-event-controllers.h"

G_BEGIN_DECLS

typedef struct _SugarCursorTracker SugarCursorTracker;
typedef struct _SugarCursorTrackerClass SugarCursorTrackerClass;

#define SUGAR_TYPE_CURSOR_TRACKER              (sugar_cursor_tracker_get_type())
#define SUGAR_CURSOR_TRACKER(object)           (G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_CURSOR_TRACKER, SugarCursorTracker))
#define SUGAR_CURSOR_TRACKER_CLASS(klass)      (G_TYPE_CHACK_CLASS_CAST((klass), SUGAR_TYPE_CURSOR_TRACKER, SugarCursorTrackerClass))
#define SUGAR_IS_CURSOR_TRACKER(object)        (G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_CURSOR_TRACKER))
#define SUGAR_IS_CURSOR_TRACKER_CLASS(klass)   (G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_CURSOR_TRACKER))
#define SUGAR_CURSOR_TRACKER_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), SUGAR_TYPE_CURSOR_TRACKER, SugarCursorTrackerClass))

struct _SugarCursorTracker {
	GObject parent_instance;
	gpointer _priv;
};

struct _SugarCursorTrackerClass {
	GObjectClass parent_class;
};

GType                sugar_cursor_tracker_get_type (void);
SugarCursorTracker * sugar_cursor_tracker_new      (void);

G_END_DECLS

#endif /* __SUGAR_CURSOR_TRACKER_H__ */

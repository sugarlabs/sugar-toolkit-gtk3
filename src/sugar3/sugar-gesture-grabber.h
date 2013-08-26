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
 * Author: Carlos Garnacho  <carlos@lanedo.com>
 */

#ifndef __SUGAR_GESTURE_GRABBER_H__
#define __SUGAR_GESTURE_GRABBER_H__

#include <gtk/gtk.h>
#include "event-controller/sugar-event-controllers.h"

G_BEGIN_DECLS

typedef struct _SugarGestureGrabber SugarGestureGrabber;
typedef struct _SugarGestureGrabberClass SugarGestureGrabberClass;

#define SUGAR_TYPE_GESTURE_GRABBER              (sugar_gesture_grabber_get_type())
#define SUGAR_GESTURE_GRABBER(object)           (G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_GESTURE_GRABBER, SugarGestureGrabber))
#define SUGAR_GESTURE_GRABBER_CLASS(klass)      (G_TYPE_CHACK_CLASS_CAST((klass), SUGAR_TYPE_GESTURE_GRABBER, SugarGestureGrabberClass))
#define SUGAR_IS_GESTURE_GRABBER(object)        (G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_GESTURE_GRABBER))
#define SUGAR_IS_GESTURE_GRABBER_CLASS(klass)   (G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_GESTURE_GRABBER))
#define SUGAR_GESTURE_GRABBER_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), SUGAR_TYPE_GESTURE_GRABBER, SugarGestureGrabberClass))

struct _SugarGestureGrabber {
	GObject parent_instance;
	gpointer _priv;
};

struct _SugarGestureGrabberClass {
	GObjectClass parent_class;
};

GType                 sugar_gesture_grabber_get_type (void);
SugarGestureGrabber * sugar_gesture_grabber_new      (void);
void                  sugar_gesture_grabber_add      (SugarGestureGrabber  *grabber,
						      SugarEventController *controller,
						      const GdkRectangle   *rect);
void		      sugar_gesture_grabber_remove   (SugarGestureGrabber  *grabber,
						      SugarEventController *controller);

G_END_DECLS

#endif /* __SUGAR_GESTURE_GRABBER_H__ */

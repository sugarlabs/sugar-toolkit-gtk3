/*
 * Copyright (C) 2012, One Laptop Per Child.
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
 * Author(s): Carlos Garnacho <carlos@lanedo.com>
 */

#if !defined (__SUGAR_CONTROLLERS_H_INSIDE__) && !defined (SUGAR_TOOLKIT_COMPILATION)
#error "Only <sugar/event-controller/sugar-event-controllers.h> can be included directly."
#endif

#ifndef __SUGAR_SWIPE_CONTROLLER_H__
#define __SUGAR_SWIPE_CONTROLLER_H__

#include "sugar-event-controller.h"
#include <gtk/gtk.h>

G_BEGIN_DECLS

#define SUGAR_TYPE_SWIPE_CONTROLLER         (sugar_swipe_controller_get_type ())
#define SUGAR_SWIPE_CONTROLLER(o)           (G_TYPE_CHECK_INSTANCE_CAST ((o), SUGAR_TYPE_SWIPE_CONTROLLER, SugarSwipeController))
#define SUGAR_SWIPE_CONTROLLER_CLASS(k)     (G_TYPE_CHECK_CLASS_CAST ((k), SUGAR_TYPE_SWIPE_CONTROLLER, SugarSwipeControllerClass))
#define SUGAR_IS_SWIPE_CONTROLLER(o)        (G_TYPE_CHECK_INSTANCE_TYPE ((o), SUGAR_TYPE_SWIPE_CONTROLLER))
#define SUGAR_IS_SWIPE_CONTROLLER_CLASS(k)  (G_TYPE_CHECK_CLASS_TYPE ((k), SUGAR_TYPE_SWIPE_CONTROLLER))
#define SUGAR_SWIPE_CONTROLLER_GET_CLASS(o) (G_TYPE_INSTANCE_GET_CLASS ((o), SUGAR_TYPE_SWIPE_CONTROLLER, SugarSwipeControllerClass))

typedef struct _SugarSwipeController SugarSwipeController;
typedef struct _SugarSwipeControllerClass SugarSwipeControllerClass;

typedef enum {
  SUGAR_SWIPE_DIRECTION_LEFT,
  SUGAR_SWIPE_DIRECTION_RIGHT,
  SUGAR_SWIPE_DIRECTION_UP,
  SUGAR_SWIPE_DIRECTION_DOWN
} SugarSwipeDirection;

typedef enum {
  SUGAR_SWIPE_DIRECTION_FLAG_LEFT  = 1 << SUGAR_SWIPE_DIRECTION_LEFT,
  SUGAR_SWIPE_DIRECTION_FLAG_RIGHT = 1 << SUGAR_SWIPE_DIRECTION_RIGHT,
  SUGAR_SWIPE_DIRECTION_FLAG_UP    = 1 << SUGAR_SWIPE_DIRECTION_UP,
  SUGAR_SWIPE_DIRECTION_FLAG_DOWN  = 1 << SUGAR_SWIPE_DIRECTION_DOWN,
} SugarSwipeDirectionFlags;

struct _SugarSwipeController
{
  SugarEventController parent_instance;
  gpointer _priv;
};

struct _SugarSwipeControllerClass
{
  SugarEventControllerClass parent_class;

  void (* swipe_ended) (SugarSwipeController *controller,
                        SugarSwipeDirection   direction);
};

GType                  sugar_swipe_controller_get_type (void) G_GNUC_CONST;
SugarEventController * sugar_swipe_controller_new      (SugarSwipeDirectionFlags directions);

G_END_DECLS

#endif /* __SUGAR_SWIPE_CONTROLLER_H__ */

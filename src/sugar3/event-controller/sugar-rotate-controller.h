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

#ifndef __SUGAR_ROTATE_CONTROLLER_H__
#define __SUGAR_ROTATE_CONTROLLER_H__

#include "sugar-touch-controller.h"
#include <gtk/gtk.h>

G_BEGIN_DECLS

#define SUGAR_TYPE_ROTATE_CONTROLLER         (sugar_rotate_controller_get_type ())
#define SUGAR_ROTATE_CONTROLLER(o)           (G_TYPE_CHECK_INSTANCE_CAST ((o), SUGAR_TYPE_ROTATE_CONTROLLER, SugarRotateController))
#define SUGAR_ROTATE_CONTROLLER_CLASS(k)     (G_TYPE_CHECK_CLASS_CAST ((k), SUGAR_TYPE_ROTATE_CONTROLLER, SugarRotateControllerClass))
#define SUGAR_IS_ROTATE_CONTROLLER(o)        (G_TYPE_CHECK_INSTANCE_TYPE ((o), SUGAR_TYPE_ROTATE_CONTROLLER))
#define SUGAR_IS_ROTATE_CONTROLLER_CLASS(k)  (G_TYPE_CHECK_CLASS_TYPE ((k), SUGAR_TYPE_ROTATE_CONTROLLER))
#define SUGAR_ROTATE_CONTROLLER_GET_CLASS(o) (G_TYPE_INSTANCE_GET_CLASS ((o), SUGAR_TYPE_ROTATE_CONTROLLER, SugarRotateControllerClass))

typedef struct _SugarRotateController SugarRotateController;
typedef struct _SugarRotateControllerClass SugarRotateControllerClass;

struct _SugarRotateController
{
  SugarTouchController parent_instance;
  gpointer _priv;
};

struct _SugarRotateControllerClass
{
  SugarTouchControllerClass parent_class;

  void (* angle_changed) (SugarRotateController *controller,
                          gdouble                angle,
                          gdouble                delta);
};

GType                  sugar_rotate_controller_get_type        (void) G_GNUC_CONST;
SugarEventController * sugar_rotate_controller_new             (void);

gboolean               sugar_rotate_controller_get_angle_delta (SugarRotateController *controller,
                                                                gdouble               *delta);


G_END_DECLS

#endif /* __SUGAR_ROTATE_CONTROLLER_H__ */

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

#ifndef __SUGAR_ZOOM_CONTROLLER_H__
#define __SUGAR_ZOOM_CONTROLLER_H__

#include "sugar-touch-controller.h"
#include <gtk/gtk.h>

G_BEGIN_DECLS

#define SUGAR_TYPE_ZOOM_CONTROLLER         (sugar_zoom_controller_get_type ())
#define SUGAR_ZOOM_CONTROLLER(o)           (G_TYPE_CHECK_INSTANCE_CAST ((o), SUGAR_TYPE_ZOOM_CONTROLLER, SugarZoomController))
#define SUGAR_ZOOM_CONTROLLER_CLASS(k)     (G_TYPE_CHECK_CLASS_CAST ((k), SUGAR_TYPE_ZOOM_CONTROLLER, SugarZoomControllerClass))
#define SUGAR_IS_ZOOM_CONTROLLER(o)        (G_TYPE_CHECK_INSTANCE_TYPE ((o), SUGAR_TYPE_ZOOM_CONTROLLER))
#define SUGAR_IS_ZOOM_CONTROLLER_CLASS(k)  (G_TYPE_CHECK_CLASS_TYPE ((k), SUGAR_TYPE_ZOOM_CONTROLLER))
#define SUGAR_ZOOM_CONTROLLER_GET_CLASS(o) (G_TYPE_INSTANCE_GET_CLASS ((o), SUGAR_TYPE_ZOOM_CONTROLLER, SugarZoomControllerClass))

typedef struct _SugarZoomController SugarZoomController;
typedef struct _SugarZoomControllerClass SugarZoomControllerClass;

struct _SugarZoomController
{
  SugarTouchController parent_instance;
  gpointer _priv;
};

struct _SugarZoomControllerClass
{
  SugarTouchControllerClass parent_class;

  void (* scale_changed) (SugarZoomController *controller,
                          gdouble              scale);
};

GType                  sugar_zoom_controller_get_type        (void) G_GNUC_CONST;
SugarEventController * sugar_zoom_controller_new             (void);
gboolean               sugar_zoom_controller_get_scale_delta (SugarZoomController *controller,
                                                              gdouble             *scale);

G_END_DECLS

#endif /* __SUGAR_ZOOM_CONTROLLER_H__ */

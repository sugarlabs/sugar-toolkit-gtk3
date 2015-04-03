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

#ifndef __SUGAR_LONG_PRESS_CONTROLLER_H__
#define __SUGAR_LONG_PRESS_CONTROLLER_H__

#include "sugar-event-controller.h"
#include <gtk/gtk.h>

G_BEGIN_DECLS

#define SUGAR_TYPE_LONG_PRESS_CONTROLLER         (sugar_long_press_controller_get_type ())
#define SUGAR_LONG_PRESS_CONTROLLER(o)           (G_TYPE_CHECK_INSTANCE_CAST ((o), SUGAR_TYPE_LONG_PRESS_CONTROLLER, SugarLongPressController))
#define SUGAR_LONG_PRESS_CONTROLLER_CLASS(k)     (G_TYPE_CHECK_CLASS_CAST ((k), SUGAR_TYPE_LONG_PRESS_CONTROLLER, SugarLongPressControllerClass))
#define SUGAR_IS_LONG_PRESS_CONTROLLER(o)        (G_TYPE_CHECK_INSTANCE_TYPE ((o), SUGAR_TYPE_LONG_PRESS_CONTROLLER))
#define SUGAR_IS_LONG_PRESS_CONTROLLER_CLASS(k)  (G_TYPE_CHECK_CLASS_TYPE ((k), SUGAR_TYPE_LONG_PRESS_CONTROLLER))
#define SUGAR_LONG_PRESS_CONTROLLER_GET_CLASS(o) (G_TYPE_INSTANCE_GET_CLASS ((o), SUGAR_TYPE_LONG_PRESS_CONTROLLER, SugarLongPressControllerClass))

typedef struct _SugarLongPressController SugarLongPressController;
typedef struct _SugarLongPressControllerClass SugarLongPressControllerClass;

struct _SugarLongPressController
{
  SugarEventController parent_instance;
  gpointer _priv;
};

struct _SugarLongPressControllerClass
{
  SugarEventControllerClass parent_class;

  void (* pressed) (SugarLongPressController *controller,
                    gint                      x,
                    gint                      y);
};

GType                  sugar_long_press_controller_get_type (void) G_GNUC_CONST;
SugarEventController * sugar_long_press_controller_new      (void);

G_END_DECLS

#endif /* __SUGAR_LONG_PRESS_CONTROLLER_H__ */

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

#ifndef __SUGAR_EVENT_CONTROLLER_H__
#define __SUGAR_EVENT_CONTROLLER_H__

#include <gtk/gtk.h>

G_BEGIN_DECLS

#define SUGAR_TYPE_EVENT_CONTROLLER         (sugar_event_controller_get_type ())
#define SUGAR_EVENT_CONTROLLER(o)           (G_TYPE_CHECK_INSTANCE_CAST ((o), SUGAR_TYPE_EVENT_CONTROLLER, SugarEventController))
#define SUGAR_EVENT_CONTROLLER_CLASS(k)     (G_TYPE_CHECK_CLASS_CAST ((k), SUGAR_TYPE_EVENT_CONTROLLER, SugarEventControllerClass))
#define SUGAR_IS_EVENT_CONTROLLER(o)        (G_TYPE_CHECK_INSTANCE_TYPE ((o), SUGAR_TYPE_EVENT_CONTROLLER))
#define SUGAR_IS_EVENT_CONTROLLER_CLASS(k)  (G_TYPE_CHECK_CLASS_TYPE ((k), SUGAR_TYPE_EVENT_CONTROLLER))
#define SUGAR_EVENT_CONTROLLER_GET_CLASS(o) (G_TYPE_INSTANCE_GET_CLASS ((o), SUGAR_TYPE_EVENT_CONTROLLER, SugarEventControllerClass))

typedef struct _SugarEventController SugarEventController;
typedef struct _SugarEventControllerClass SugarEventControllerClass;

typedef enum {
  SUGAR_EVENT_CONTROLLER_STATE_NONE,
  SUGAR_EVENT_CONTROLLER_STATE_COLLECTING,
  SUGAR_EVENT_CONTROLLER_STATE_RECOGNIZED,
  SUGAR_EVENT_CONTROLLER_STATE_NOT_RECOGNIZED
} SugarEventControllerState;

typedef enum {
  SUGAR_EVENT_CONTROLLER_FLAG_NONE = 0,
  SUGAR_EVENT_CONTROLLER_FLAG_EXCLUSIVE = 1 << 0
} SugarEventControllerFlags;

struct _SugarEventController
{
  GObject parent_instance;
  gpointer _priv;
};

struct _SugarEventControllerClass
{
  GObjectClass parent_class;

  /* Signals */
  void                      (* began)        (SugarEventController *controller);
  void                      (* updated)      (SugarEventController *controller);
  void                      (* ended)        (SugarEventController *controller);

  /* vmethods */
  gboolean                  (* handle_event) (SugarEventController *controller,
                                              GdkEvent             *event);
  SugarEventControllerState (* get_state)    (SugarEventController *controller);
  void                      (* reset)        (SugarEventController *controller);
};

GType     sugar_event_controller_get_type     (void) G_GNUC_CONST;
gboolean  sugar_event_controller_handle_event (SugarEventController *controller,
					       GdkEvent             *event);
gboolean  sugar_event_controller_attach       (SugarEventController      *controller,
					       GtkWidget                 *widget,
                                               SugarEventControllerFlags  flags);
gboolean  sugar_event_controller_detach       (SugarEventController      *controller,
					       GtkWidget                 *widget);
gboolean  sugar_event_controller_reset        (SugarEventController *controller);

SugarEventControllerState
          sugar_event_controller_get_state    (SugarEventController *controller);

G_END_DECLS

#endif /* __SUGAR_EVENT_CONTROLLER_H__ */

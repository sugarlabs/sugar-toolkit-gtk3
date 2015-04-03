/* eggsmclient.h
 * Copyright (C) 2007 Novell, Inc.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#ifndef __EGG_SM_CLIENT_XSMP_H__
#define __EGG_SM_CLIENT_XSMP_H__

#include <glib-object.h>
#include <X11/SM/SMlib.h>

G_BEGIN_DECLS


#define EGG_TYPE_SM_CLIENT_XSMP            (egg_sm_client_xsmp_get_type ())
#define EGG_SM_CLIENT_XSMP(obj)            (G_TYPE_CHECK_INSTANCE_CAST ((obj), EGG_TYPE_SM_CLIENT_XSMP, EggSMClientXSMP))
#define EGG_SM_CLIENT_XSMP_CLASS(klass)    (G_TYPE_CHECK_CLASS_CAST ((klass), EGG_TYPE_SM_CLIENT_XSMP, EggSMClientXSMPClass))
#define EGG_IS_SM_CLIENT_XSMP(obj)         (G_TYPE_CHECK_INSTANCE_TYPE ((obj), EGG_TYPE_SM_CLIENT_XSMP))
#define EGG_IS_SM_CLIENT_XSMP_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), EGG_TYPE_SM_CLIENT_XSMP))
#define EGG_SM_CLIENT_XSMP_GET_CLASS(obj)  (G_TYPE_INSTANCE_GET_CLASS ((obj), EGG_TYPE_SM_CLIENT_XSMP, EggSMClientXSMPClass))

typedef struct _EggSMClientXSMP        EggSMClientXSMP;
typedef struct _EggSMClientXSMPClass   EggSMClientXSMPClass;

/* These mostly correspond to the similarly-named states in section
 * 9.1 of the XSMP spec. Some of the states there aren't represented
 * here, because we don't need them. SHUTDOWN_CANCELLED is slightly
 * different from the spec; we use it when the client is IDLE after a
 * ShutdownCancelled message, but the application is still interacting
 * and doesn't know the shutdown has been cancelled yet.
 */
typedef enum
{
  XSMP_STATE_START,
  XSMP_STATE_IDLE,
  XSMP_STATE_SAVE_YOURSELF,
  XSMP_STATE_INTERACT_REQUEST,
  XSMP_STATE_INTERACT,
  XSMP_STATE_SAVE_YOURSELF_DONE,
  XSMP_STATE_SHUTDOWN_CANCELLED,
  XSMP_STATE_CONNECTION_CLOSED,
} EggSMClientXSMPState;

struct _EggSMClientXSMP
{
  EggSMClient parent;

  SmcConn connection;
  char *client_id;

  EggSMClientXSMPState state;
  char **restart_command;
  gboolean set_restart_command;
  int restart_style;

  guint idle;

  /* Current SaveYourself state */
  guint expecting_initial_save_yourself : 1;
  guint need_save_state : 1;
  guint need_quit_requested : 1;
  guint interact_errors : 1;
  guint shutting_down : 1;

  /* Todo list */
  guint waiting_to_emit_quit : 1;
  guint waiting_to_emit_quit_cancelled : 1;
  guint waiting_to_save_myself : 1;

};

struct _EggSMClientXSMPClass
{
  EggSMClientClass parent_class;

};

GType            egg_sm_client_xsmp_get_type            (void) G_GNUC_CONST;

G_END_DECLS

#endif /* __EGG_SM_CLIENT_XSMP_H__ */

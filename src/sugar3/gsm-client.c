/* client.c
 * Copyright (C) 2007 Novell, Inc.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 * 02111-1307, USA.
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "gsm-client.h"

enum {
  SAVED_STATE,
  REQUEST_PHASE2,
  REQUEST_INTERACTION,
  INTERACTION_DONE,
  SAVE_YOURSELF_DONE,
  DISCONNECTED,
  LAST_SIGNAL
};

static guint signals[LAST_SIGNAL] = { 0 };

G_DEFINE_TYPE (GsmClient, gsm_client, G_TYPE_OBJECT)

static void
gsm_client_init (GsmClient *client)
{
  ;
}

static void
gsm_client_class_init (GsmClientClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);

  signals[SAVED_STATE] =
    g_signal_new ("saved_state",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (GsmClientClass, saved_state),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE,
                  0);

  signals[REQUEST_PHASE2] =
    g_signal_new ("request_phase2",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (GsmClientClass, request_phase2),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE,
                  0);

  signals[REQUEST_INTERACTION] =
    g_signal_new ("request_interaction",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (GsmClientClass, request_interaction),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE,
                  0);

  signals[INTERACTION_DONE] =
    g_signal_new ("interaction_done",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (GsmClientClass, interaction_done),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__BOOLEAN,
                  G_TYPE_NONE,
                  1, G_TYPE_BOOLEAN);

  signals[SAVE_YOURSELF_DONE] =
    g_signal_new ("save_yourself_done",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (GsmClientClass, save_yourself_done),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE,
                  0);

  signals[DISCONNECTED] =
    g_signal_new ("disconnected",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (GsmClientClass, disconnected),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE,
                  0);

}

const char *
gsm_client_get_client_id (GsmClient *client)
{
  g_return_val_if_fail (GSM_IS_CLIENT (client), NULL);

  return GSM_CLIENT_GET_CLASS (client)->get_client_id (client);
}

pid_t
gsm_client_get_pid (GsmClient *client)
{
  g_return_val_if_fail (GSM_IS_CLIENT (client), -1);

  return GSM_CLIENT_GET_CLASS (client)->get_pid (client);
}

char *
gsm_client_get_desktop_file (GsmClient *client)
{
  g_return_val_if_fail (GSM_IS_CLIENT (client), NULL);

  return GSM_CLIENT_GET_CLASS (client)->get_desktop_file (client);
}

char *
gsm_client_get_restart_command (GsmClient *client)
{
  g_return_val_if_fail (GSM_IS_CLIENT (client), NULL);

  return GSM_CLIENT_GET_CLASS (client)->get_restart_command (client);
}

char *
gsm_client_get_discard_command (GsmClient *client)
{
  g_return_val_if_fail (GSM_IS_CLIENT (client), NULL);

  return GSM_CLIENT_GET_CLASS (client)->get_discard_command (client);
}

gboolean
gsm_client_get_autorestart (GsmClient *client)
{
  g_return_val_if_fail (GSM_IS_CLIENT (client), FALSE);

  return GSM_CLIENT_GET_CLASS (client)->get_autorestart (client);
}

void
gsm_client_save_state (GsmClient *client)
{
  g_return_if_fail (GSM_IS_CLIENT (client));
}

void
gsm_client_restart (GsmClient *client, GError **error)
{
  g_return_if_fail (GSM_IS_CLIENT (client));

  GSM_CLIENT_GET_CLASS (client)->restart (client, error);
}

void
gsm_client_save_yourself (GsmClient *client,
			  gboolean   save_state)
{
  g_return_if_fail (GSM_IS_CLIENT (client));

  GSM_CLIENT_GET_CLASS (client)->save_yourself (client, save_state);
}

void
gsm_client_save_yourself_phase2 (GsmClient *client)
{
  g_return_if_fail (GSM_IS_CLIENT (client));

  GSM_CLIENT_GET_CLASS (client)->save_yourself_phase2 (client);
}

void
gsm_client_interact (GsmClient *client)
{
  g_return_if_fail (GSM_IS_CLIENT (client));

  GSM_CLIENT_GET_CLASS (client)->interact (client);
}

void
gsm_client_shutdown_cancelled (GsmClient *client)
{
  g_return_if_fail (GSM_IS_CLIENT (client));

  GSM_CLIENT_GET_CLASS (client)->shutdown_cancelled (client);
}

void
gsm_client_die (GsmClient *client)
{
  g_return_if_fail (GSM_IS_CLIENT (client));

  GSM_CLIENT_GET_CLASS (client)->die (client);
}

void
gsm_client_saved_state (GsmClient *client)
{
  g_signal_emit (client, signals[SAVED_STATE], 0);
}

void
gsm_client_request_phase2 (GsmClient *client)
{
  g_signal_emit (client, signals[REQUEST_PHASE2], 0);
}

void
gsm_client_request_interaction (GsmClient *client)
{
  g_signal_emit (client, signals[REQUEST_INTERACTION], 0);
}

void
gsm_client_interaction_done (GsmClient *client, gboolean cancel_shutdown)
{
  g_signal_emit (client, signals[INTERACTION_DONE], 0, cancel_shutdown);
}

void
gsm_client_save_yourself_done (GsmClient *client)
{
  g_signal_emit (client, signals[SAVE_YOURSELF_DONE], 0);
}

void
gsm_client_disconnected (GsmClient *client)
{
  g_signal_emit (client, signals[DISCONNECTED], 0);
}


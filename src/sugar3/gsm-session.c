/* session.c
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

#include <string.h>

#include "gsm-session.h"
#include "gsm-app.h"
#include "gsm-xsmp.h"

GsmSession *global_session;

static void initiate_shutdown         (GsmSession *session);

static void session_shutdown          (GsmSession *session);

static void client_saved_state         (GsmClient *client,
					gpointer   data);
static void client_request_phase2      (GsmClient *client,
					gpointer   data);
static void client_request_interaction (GsmClient *client,
					gpointer   data);
static void client_interaction_done    (GsmClient *client,
					gboolean   cancel_shutdown,
					gpointer   data);
static void client_save_yourself_done  (GsmClient *client,
					gpointer   data);
static void client_disconnected        (GsmClient *client,
					gpointer   data);

struct _GsmSession {
  GObject parent;

  char *name;

  /* Current status */
  GsmSessionPhase phase;
  guint timeout;
  GSList *pending_apps;

  /* SM clients */
  GSList *clients;

  /* When shutdown starts, all clients are put into shutdown_clients.
   * If they request phase2, they are moved from shutdown_clients to
   * phase2_clients. If they request interaction, they are appended
   * to interact_clients (the first client in interact_clients is
   * the one currently interacting). If they report that they're done,
   * they're removed from shutdown_clients/phase2_clients.
   *
   * Once shutdown_clients is empty, phase2 starts. Once phase2_clients
   * is empty, shutdown is complete.
   */
  GSList *shutdown_clients;
  GSList *interact_clients;
  GSList *phase2_clients;

  /* List of clients which were disconnected due to disabled condition
   * and shouldn't be automatically restarted */
  GSList *condition_clients;
};

struct _GsmSessionClass
{
  GObjectClass parent_class;

  void (* shutdown_completed) (GsmSession *client);
};

enum {
  SHUTDOWN_COMPLETED,
  LAST_SIGNAL
};

static guint signals[LAST_SIGNAL] = { 0 };

G_DEFINE_TYPE (GsmSession, gsm_session, G_TYPE_OBJECT)

#define GSM_SESSION_PHASE_TIMEOUT 10 /* seconds */

void
gsm_session_init (GsmSession *session)
{
  session->name = NULL;
  session->clients = NULL;
  session->condition_clients = NULL;
}

static void
gsm_session_class_init (GsmSessionClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);

  signals[SHUTDOWN_COMPLETED] =
    g_signal_new ("shutdown_completed",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_LAST,
                  G_STRUCT_OFFSET (GsmSessionClass, shutdown_completed),
                  NULL, NULL,
                  g_cclosure_marshal_VOID__VOID,
                  G_TYPE_NONE,
                  0);
}


/**
 * gsm_session_set_name:
 * @session: session instance
 * @name: name of the session
 *
 * Sets the name of a running session.
 **/
void
gsm_session_set_name (GsmSession *session, const char *name)
{
  if (session->name)
    g_free (session->name);

  session->name = g_strdup (name);
}

static void start_phase (GsmSession *session);

static void
end_phase (GsmSession *session)
{
  g_slist_free (session->pending_apps);
  session->pending_apps = NULL;

  g_debug ("ending phase %d\n", session->phase);

  session->phase++;

  if (session->phase < GSM_SESSION_PHASE_RUNNING)
    start_phase (session);
}

static void
app_registered (GsmApp *app, gpointer data)
{
  GsmSession *session = data;

  session->pending_apps = g_slist_remove (session->pending_apps, app);
  g_signal_handlers_disconnect_by_func (app, app_registered, session);

  if (!session->pending_apps)
    {
      if (session->timeout > 0)
        {
          g_source_remove (session->timeout);
          session->timeout = 0;
        }

      end_phase (session);
    }
}

static gboolean
phase_timeout (gpointer data)
{
  GsmSession *session = data;
  GSList *a;

  session->timeout = 0;

  for (a = session->pending_apps; a; a = a->next)
    {
      g_warning ("Application '%s' failed to register before timeout",
		 gsm_app_get_basename (a->data));
      g_signal_handlers_disconnect_by_func (a->data, app_registered, session);

      /* FIXME: what if the app was filling in a required slot? */
    }

  end_phase (session);
  return FALSE;
}

static void
start_phase (GsmSession *session)
{
  g_debug ("starting phase %d\n", session->phase);

  g_slist_free (session->pending_apps);
  session->pending_apps = NULL;

  if (session->pending_apps)
    {
      if (session->phase < GSM_SESSION_PHASE_APPLICATION)
	{
	  session->timeout = g_timeout_add_seconds (GSM_SESSION_PHASE_TIMEOUT,
					    phase_timeout, session);
	}
    }
  else
    end_phase (session);
}

void
gsm_session_start (GsmSession *session)
{
  session->phase = GSM_SESSION_PHASE_INITIALIZATION;

  start_phase (session);
}

GsmSessionPhase
gsm_session_get_phase (GsmSession *session)
{
  return session->phase;
}

char *
gsm_session_register_client (GsmSession *session,
			     GsmClient  *client,
			     const char *id)
{
  GSList *a;
  char *client_id = NULL;

  /* If we're shutting down, we don't accept any new session
     clients. */
  if (session->phase == GSM_SESSION_PHASE_SHUTDOWN)
    return FALSE;

  if (id == NULL)
    client_id = gsm_xsmp_generate_client_id ();
  else
    {
      for (a = session->clients; a; a = a->next)
        {
          GsmClient *client = GSM_CLIENT (a->data);

          /* We can't have two clients with the same id. */
          if (!strcmp (id, gsm_client_get_client_id (client)))
            {
              return NULL;
            }
        }

      client_id = g_strdup (id);
    }

  g_debug ("Adding new client %s to session", id);

  g_signal_connect (client, "saved_state",
		    G_CALLBACK (client_saved_state), session);
  g_signal_connect (client, "request_phase2",
		    G_CALLBACK (client_request_phase2), session);
  g_signal_connect (client, "request_interaction",
		    G_CALLBACK (client_request_interaction), session);
  g_signal_connect (client, "interaction_done",
		    G_CALLBACK (client_interaction_done), session);
  g_signal_connect (client, "save_yourself_done",
		    G_CALLBACK (client_save_yourself_done), session);
  g_signal_connect (client, "disconnected",
		    G_CALLBACK (client_disconnected), session);

  session->clients = g_slist_prepend (session->clients, client);

  /* If it's a brand new client id, we just accept the client*/
  if (id == NULL)
    return client_id;

  /* If we're starting up the session, try to match the new client
   * with one pending apps for the current phase. If not, try to match
   * with any of the autostarted apps. */
  if (session->phase < GSM_SESSION_PHASE_APPLICATION)
    a = session->pending_apps;

  for (; a; a = a->next)
    {
      GsmApp *app = GSM_APP (a->data);

      if (!strcmp (client_id, app->client_id))
        {
          gsm_app_registered (app);
          return client_id;
        }
    }

  g_free (client_id);

  return NULL;
}

static void
client_saved_state (GsmClient *client, gpointer data)
{
  /* FIXME */
}

void
gsm_session_initiate_shutdown (GsmSession *session)
{
  if (session->phase == GSM_SESSION_PHASE_SHUTDOWN)
    {
      /* Already shutting down, nothing more to do */
      return;
    }

  initiate_shutdown (session);
}

static void
session_shutdown_phase2 (GsmSession *session)
{
  GSList *cl;

  for (cl = session->phase2_clients; cl; cl = cl->next)
    gsm_client_save_yourself_phase2 (cl->data);
}

static void
session_cancel_shutdown (GsmSession *session)
{
  GSList *cl;

  session->phase = GSM_SESSION_PHASE_RUNNING;

  g_slist_free (session->shutdown_clients);
  session->shutdown_clients = NULL;
  g_slist_free (session->interact_clients);
  session->interact_clients = NULL;
  g_slist_free (session->phase2_clients);
  session->phase2_clients = NULL;

  for (cl = session->clients; cl; cl = cl->next)
    gsm_client_shutdown_cancelled (cl->data);
}

void
gsm_session_cancel_shutdown (GsmSession *session)
{
  if (session == NULL || session->phase != GSM_SESSION_PHASE_SHUTDOWN)
    {
      g_warning ("Session is not in shutdown mode");
      return;
    }

  session_cancel_shutdown (session);
}

static void
initiate_shutdown (GsmSession *session)
{
  GSList *cl;

  session->phase = GSM_SESSION_PHASE_SHUTDOWN;

  if (session->clients == NULL)
    session_shutdown (session);

  for (cl = session->clients; cl; cl = cl->next)
    {
      GsmClient *client = GSM_CLIENT (cl->data);

      session->shutdown_clients =
	g_slist_prepend (session->shutdown_clients, client);

      gsm_client_save_yourself (client, FALSE);
    }
}

static void
session_shutdown (GsmSession *session)
{
  GSList *cl;

  /* FIXME: do this in reverse phase order */
  for (cl = session->clients; cl; cl = cl->next)
    gsm_client_die (cl->data);

  g_signal_emit (session, signals[SHUTDOWN_COMPLETED], 0);
}

static void
client_request_phase2 (GsmClient *client, gpointer data)
{
  GsmSession *session = data;

  /* Move the client from shutdown_clients to phase2_clients */

  session->shutdown_clients =
    g_slist_remove (session->shutdown_clients, client);
  session->phase2_clients =
    g_slist_prepend (session->phase2_clients, client);
}

static void
client_request_interaction (GsmClient *client, gpointer data)
{
  GsmSession *session = data;

  session->interact_clients =
    g_slist_append (session->interact_clients, client);

  if (!session->interact_clients->next)
    gsm_client_interact (client);
}

static void
client_interaction_done (GsmClient *client, gboolean cancel_shutdown,
			 gpointer data)
{
  GsmSession *session = data;

  g_return_if_fail (session->interact_clients &&
		    (GsmClient *)session->interact_clients->data == client);

  if (cancel_shutdown)
    {
      session_cancel_shutdown (session);
      return;
    }

  /* Remove this client from interact_clients, and if there's another
   * client waiting to interact, let it interact now.
   */
  session->interact_clients =
    g_slist_remove (session->interact_clients, client);
  if (session->interact_clients)
    gsm_client_interact (session->interact_clients->data);
}

static void
client_save_yourself_done (GsmClient *client, gpointer data)
{
  GsmSession *session = data;

  session->shutdown_clients =
    g_slist_remove (session->shutdown_clients, client);
  session->interact_clients =
    g_slist_remove (session->interact_clients, client);
  session->phase2_clients =
    g_slist_remove (session->phase2_clients, client);

  if (session->phase == GSM_SESSION_PHASE_SHUTDOWN &&
      !session->shutdown_clients)
    {
      if (session->phase2_clients)
	session_shutdown_phase2 (session);
      else
	session_shutdown (session);
    }
}

static void
client_disconnected (GsmClient *client, gpointer data)
{
  GsmSession *session = data;
  gboolean is_condition_client = FALSE;

  session->clients =
    g_slist_remove (session->clients, client);
  session->shutdown_clients =
    g_slist_remove (session->shutdown_clients, client);
  session->interact_clients =
    g_slist_remove (session->interact_clients, client);
  session->phase2_clients =
    g_slist_remove (session->phase2_clients, client);

  if (g_slist_find (session->condition_clients, client))
    {
      session->condition_clients =
        g_slist_remove (session->condition_clients, client);

      is_condition_client = TRUE;
    }

  if (session->phase != GSM_SESSION_PHASE_SHUTDOWN &&
      gsm_client_get_autorestart (client) &&
      !is_condition_client)
    {
      GError *error = NULL;

      gsm_client_restart (client, &error);

      if (error)
      {
        g_warning ("Error on restarting session client: %s", error->message);
        g_clear_error (&error);
      }
    }

  g_object_unref (client);
}

/**
 * gsm_session_create_global
 *
 * Creates a new GSM_SESSION
 *
 * Returns: (transfer full): returns GSM_SESSION
 **/

GsmSession *
gsm_session_create_global (void)
{
    global_session = GSM_SESSION(g_object_new (GSM_TYPE_SESSION, NULL));
    return global_session;
}

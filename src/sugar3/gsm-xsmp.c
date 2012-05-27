/* xsmp.c
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

#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>

#include <glib.h>
#include <glib/gi18n.h>

#include "gsm-client-xsmp.h"
#include "gsm-xsmp.h"

#include <X11/ICE/ICElib.h>
#include <X11/ICE/ICEutil.h>
#include <X11/ICE/ICEconn.h>
#include <X11/SM/SMlib.h>

#ifdef HAVE_X11_XTRANS_XTRANS_H
/* Get the proto for _IceTransNoListen */
#define ICE_t
#define TRANS_SERVER
#include <X11/Xtrans/Xtrans.h>
#undef  ICE_t
#undef TRANS_SERVER
#endif /* HAVE_X11_XTRANS_XTRANS_H */

static IceListenObj *xsmp_sockets;
static int num_xsmp_sockets, num_local_xsmp_sockets;

static gboolean update_iceauthority    (gboolean        adding);

static gboolean accept_ice_connection  (GIOChannel     *source,
					GIOCondition    condition,
					gpointer        data);
static Status   accept_xsmp_connection (SmsConn         conn,
					SmPointer       manager_data,
					unsigned long  *mask_ret,
					SmsCallbacks   *callbacks_ret,
					char          **failure_reason_ret);

static void     ice_error_handler      (IceConn       conn,
					Bool          swap,
					int           offending_minor_opcode,
					unsigned long offending_sequence_num,
					int           error_class,
					int           severity,
					IcePointer    values);
static void     ice_io_error_handler   (IceConn       conn);
static void     sms_error_handler      (SmsConn       sms_conn,
					Bool          swap,
					int           offending_minor_opcode,
					unsigned long offending_sequence_num,
					int           error_class,
					int           severity,
					IcePointer    values);
/**
 * gsm_xsmp_init:
 *
 * Initializes XSMP. Notably, it creates the XSMP listening socket and
 * sets the SESSION_MANAGER environment variable to point to it.
 **/
char *
gsm_xsmp_init (void)
{
  char error[256];
  mode_t saved_umask;
  char *network_id_list;
  int i;

  /* Set up sane error handlers */
  IceSetErrorHandler (ice_error_handler);
  IceSetIOErrorHandler (ice_io_error_handler);
  SmsSetErrorHandler (sms_error_handler);

  /* Initialize libSM; we pass NULL for hostBasedAuthProc to disable
   * host-based authentication.
   */
  if (!SmsInitialize (PACKAGE, VERSION, accept_xsmp_connection,
		      NULL, NULL, sizeof (error), error))
    g_error("Could not initialize libSM: %s", error);

#ifdef HAVE_X11_XTRANS_XTRANS_H
  /* By default, IceListenForConnections will open one socket for each
   * transport type known to X. We don't want connections from remote
   * hosts, so for security reasons it would be best if ICE didn't
   * even open any non-local sockets. So we use an internal ICElib
   * method to disable them here. Unfortunately, there is no way to
   * ask X what transport types it knows about, so we're forced to
   * guess.
   */
  _IceTransNoListen ("tcp");
#endif

  /* Create the XSMP socket. Older versions of IceListenForConnections
   * have a bug which causes the umask to be set to 0 on certain types
   * of failures. Probably not an issue on any modern systems, but
   * we'll play it safe.
   */
  saved_umask = umask (0);
  umask (saved_umask);
  if (!IceListenForConnections (&num_xsmp_sockets, &xsmp_sockets,
				sizeof (error), error))
    g_error ("Could not create ICE listening socket: %s", error);
  umask (saved_umask);

  /* Find the local sockets in the returned socket list and move them
   * to the start of the list.
   */
  for (i = num_local_xsmp_sockets = 0; i < num_xsmp_sockets; i++)
    {
      char *id = IceGetListenConnectionString (xsmp_sockets[i]);

      if (!strncmp (id, "local/", sizeof ("local/") - 1) ||
	  !strncmp (id, "unix/", sizeof ("unix/") - 1))
	{
	  if (i > num_local_xsmp_sockets)
	    {
	      IceListenObj tmp = xsmp_sockets[i];
	      xsmp_sockets[i] = xsmp_sockets[num_local_xsmp_sockets];
	      xsmp_sockets[num_local_xsmp_sockets] = tmp;
	    }
	  num_local_xsmp_sockets++;
	}
      free (id);
    }

  if (num_local_xsmp_sockets == 0)
    g_error ("IceListenForConnections did not return a local listener!");

#ifdef HAVE_X11_XTRANS_XTRANS_H
  if (num_local_xsmp_sockets != num_xsmp_sockets)
    {
      /* Xtrans was apparently compiled with support for some
       * non-local transport besides TCP (which we disabled above); we
       * won't create IO watches on those extra sockets, so
       * connections to them will never be noticed, but they're still
       * there, which is inelegant.
       *
       * If the g_warning below is triggering for you and you want to
       * stop it, the fix is to add additional _IceTransNoListen()
       * calls above.
       */
      network_id_list =
	IceComposeNetworkIdList (num_xsmp_sockets - num_local_xsmp_sockets,
				 xsmp_sockets + num_local_xsmp_sockets);
      g_warning ("IceListenForConnections returned %d non-local listeners: %s",
		 num_xsmp_sockets - num_local_xsmp_sockets, network_id_list);
      free (network_id_list);
    }
#endif

  /* Update .ICEauthority with new auth entries for our socket */
  if (!update_iceauthority (TRUE))
    {
      /* FIXME: is this really fatal? Hm... */
      g_error ("Could not update ICEauthority file %s",
				IceAuthFileName ());
    }

  network_id_list = IceComposeNetworkIdList (num_local_xsmp_sockets,
					     xsmp_sockets);

  return network_id_list;
}

/**
 * gsm_xsmp_run:
 *
 * Sets the XSMP server to start accepting connections.
 **/
void
gsm_xsmp_run (void)
{
  GIOChannel *channel;
  int i;

  for (i = 0; i < num_local_xsmp_sockets; i++)
    {
      channel = g_io_channel_unix_new (IceGetListenConnectionNumber (xsmp_sockets[i]));
      g_io_add_watch (channel, G_IO_IN | G_IO_HUP | G_IO_ERR,
		      accept_ice_connection, xsmp_sockets[i]);
      g_io_channel_unref (channel);
    }
}

/**
 * gsm_xsmp_shutdown:
 *
 * Shuts down the XSMP server and closes the ICE listening socket
 **/
void
gsm_xsmp_shutdown (void)
{
  update_iceauthority (FALSE);

  IceFreeListenObjs (num_xsmp_sockets, xsmp_sockets);
  xsmp_sockets = NULL;
}

/**
 * gsm_xsmp_generate_client_id:
 *
 * Generates a new XSMP client ID.
 *
 * Return value: an XSMP client ID.
 **/
char *
gsm_xsmp_generate_client_id (void)
{
  static int sequence = -1;
  static guint rand1 = 0, rand2 = 0;
  static pid_t pid = 0;
  struct timeval tv;

  /* The XSMP spec defines the ID as:
   *
   * Version: "1"
   * Address type and address:
   *   "1" + an IPv4 address as 8 hex digits
   *   "2" + a DECNET address as 12 hex digits
   *   "6" + an IPv6 address as 32 hex digits
   * Time stamp: milliseconds since UNIX epoch as 13 decimal digits
   * Process-ID type and process-ID:
   *   "1" + POSIX PID as 10 decimal digits
   * Sequence number as 4 decimal digits
   *
   * XSMP client IDs are supposed to be globally unique: if
   * SmsGenerateClientID() is unable to determine a network
   * address for the machine, it gives up and returns %NULL.
   * GNOME and KDE have traditionally used a fourth address
   * format in this case:
   *   "0" + 16 random hex digits
   *
   * We don't even bother trying SmsGenerateClientID(), since the
   * user's IP address is probably "192.168.1.*" anyway, so a random
   * number is actually more likely to be globally unique.
   */

  if (!rand1)
    {
      rand1 = g_random_int ();
      rand2 = g_random_int ();
      pid = getpid ();
    }

  sequence = (sequence + 1) % 10000;
  gettimeofday (&tv, NULL);
  return g_strdup_printf ("10%.04x%.04x%.10lu%.3u%.10lu%.4d",
			  rand1, rand2,
			  (unsigned long) tv.tv_sec,
			  (unsigned) tv.tv_usec,
			  (unsigned long) pid,
			  sequence);
}

/* This is called (by glib via xsmp->ice_connection_watch) when a
 * connection is first received on the ICE listening socket. (We
 * expect that the client will then initiate XSMP on the connection;
 * if it does not, GsmClientXSMP will eventually time out and close
 * the connection.)
 *
 * FIXME: it would probably make more sense to not create a
 * GsmClientXSMP object until accept_xsmp_connection, below (and to do
 * the timing-out here in xsmp.c).
 */
static gboolean
accept_ice_connection (GIOChannel   *source,
		       GIOCondition  condition,
		       gpointer      data)
{
  IceListenObj listener = data;
  IceConn ice_conn;
  IceAcceptStatus status;
  GsmClientXSMP *client;

  g_debug ("accept_ice_connection()");

  ice_conn = IceAcceptConnection (listener, &status);
  if (status != IceAcceptSuccess)
    {
      g_debug ("IceAcceptConnection returned %d", status);
      return TRUE;
    }

  client = gsm_client_xsmp_new (ice_conn);
  ice_conn->context = client;
  return TRUE;
}

/* This is called (by libSM) when XSMP is initiated on an ICE
 * connection that was already accepted by accept_ice_connection.
 */
static Status
accept_xsmp_connection (SmsConn sms_conn, SmPointer manager_data,
			unsigned long *mask_ret, SmsCallbacks *callbacks_ret,
			char **failure_reason_ret)
{
  IceConn ice_conn;
  GsmClientXSMP *client;

  /* FIXME: what about during shutdown but before gsm_xsmp_shutdown? */
  if (!xsmp_sockets)
    {
      g_debug ("In shutdown, rejecting new client");

      *failure_reason_ret =
	strdup (_("Refusing new client connection because the session is currently being shut down\n"));
      return FALSE;
    }

  ice_conn = SmsGetIceConnection (sms_conn);
  client = ice_conn->context;

  g_return_val_if_fail (client != NULL, TRUE);

  gsm_client_xsmp_connect (client, sms_conn, mask_ret, callbacks_ret);
  return TRUE;
}

/* ICEauthority stuff */

/* Various magic numbers stolen from iceauth.c */
#define GSM_ICE_AUTH_RETRIES      10
#define GSM_ICE_AUTH_INTERVAL     2   /* 2 seconds */
#define GSM_ICE_AUTH_LOCK_TIMEOUT 600 /* 10 minutes */

#define GSM_ICE_MAGIC_COOKIE_AUTH_NAME "MIT-MAGIC-COOKIE-1"
#define GSM_ICE_MAGIC_COOKIE_LEN       16

static IceAuthFileEntry *
auth_entry_new (const char *protocol, const char *network_id)
{
  IceAuthFileEntry *file_entry;
  IceAuthDataEntry data_entry;

  file_entry = malloc (sizeof (IceAuthFileEntry));

  file_entry->protocol_name = strdup (protocol);
  file_entry->protocol_data = NULL;
  file_entry->protocol_data_length = 0;
  file_entry->network_id = strdup (network_id);
  file_entry->auth_name = strdup (GSM_ICE_MAGIC_COOKIE_AUTH_NAME);
  file_entry->auth_data = IceGenerateMagicCookie (GSM_ICE_MAGIC_COOKIE_LEN);
  file_entry->auth_data_length = GSM_ICE_MAGIC_COOKIE_LEN;

  /* Also create an in-memory copy, which is what the server will
   * actually use for checking client auth.
   */
  data_entry.protocol_name = file_entry->protocol_name;
  data_entry.network_id = file_entry->network_id;
  data_entry.auth_name = file_entry->auth_name;
  data_entry.auth_data = file_entry->auth_data;
  data_entry.auth_data_length = file_entry->auth_data_length;
  IceSetPaAuthData (1, &data_entry);

  return file_entry;
}

static gboolean
update_iceauthority (gboolean adding)
{
  char *filename = IceAuthFileName ();
  char **our_network_ids;
  FILE *fp;
  IceAuthFileEntry *auth_entry;
  GSList *entries, *e;
  int i;
  gboolean ok = FALSE;

  if (IceLockAuthFile (filename, GSM_ICE_AUTH_RETRIES, GSM_ICE_AUTH_INTERVAL,
		       GSM_ICE_AUTH_LOCK_TIMEOUT) != IceAuthLockSuccess)
    return FALSE;

  our_network_ids = g_malloc (num_local_xsmp_sockets * sizeof (char *));
  for (i = 0; i < num_local_xsmp_sockets; i++)
    our_network_ids[i] = IceGetListenConnectionString (xsmp_sockets[i]);

  entries = NULL;

  fp = fopen (filename, "r+");
  if (fp)
    {
      while ((auth_entry = IceReadAuthFileEntry (fp)) != NULL)
	{
	  /* Skip/delete entries with no network ID (invalid), or with
	   * our network ID; if we're starting up, an entry with our
	   * ID must be a stale entry left behind by an old process,
	   * and if we're shutting down, it won't be valid in the
	   * future, so either way we want to remove it from the list.
	   */
	  if (!auth_entry->network_id)
	    {
	      IceFreeAuthFileEntry (auth_entry);
	      continue;
	    }

	  for (i = 0; i < num_local_xsmp_sockets; i++)
	    {
	      if (!strcmp (auth_entry->network_id, our_network_ids[i]))
		{
		  IceFreeAuthFileEntry (auth_entry);
		  break;
		}
	    }
	  if (i != num_local_xsmp_sockets)
	    continue;

	  entries = g_slist_prepend (entries, auth_entry);
	}

      rewind (fp);
    }
  else
    {
      int fd;

      if (g_file_test (filename, G_FILE_TEST_EXISTS))
	{
	  g_warning ("Unable to read ICE authority file: %s", filename);
	  goto cleanup;
	}

      fd = open (filename, O_CREAT | O_WRONLY, 0600);
      fp = fdopen (fd, "w");
      if (!fp)
	{
	  g_warning ("Unable to write to ICE authority file: %s", filename);
	  if (fd != -1)
	    close (fd);
	  goto cleanup;
	}
    }

  if (adding)
    {
      for (i = 0; i < num_local_xsmp_sockets; i++)
	{
	  entries = g_slist_append (entries,
				    auth_entry_new ("ICE", our_network_ids[i]));
	  entries = g_slist_prepend (entries,
				     auth_entry_new ("XSMP", our_network_ids[i]));
	}
    }

  for (e = entries; e; e = e->next)
    {
      IceAuthFileEntry *auth_entry = e->data;
      IceWriteAuthFileEntry (fp, auth_entry);
      IceFreeAuthFileEntry (auth_entry);
    }
  g_slist_free (entries);

  fclose (fp);
  ok = TRUE;

 cleanup:
  IceUnlockAuthFile (filename);
  for (i = 0; i < num_local_xsmp_sockets; i++)
    free (our_network_ids[i]);
  g_free (our_network_ids);

  return ok;
}

/* Error handlers */

static void
ice_error_handler (IceConn conn, Bool swap, int offending_minor_opcode,
		   unsigned long offending_sequence, int error_class,
		   int severity, IcePointer values)
{
  g_debug ("ice_error_handler (%p, %s, %d, %lx, %d, %d)",
	   conn, swap ? "TRUE" : "FALSE", offending_minor_opcode,
	   offending_sequence, error_class, severity);

  if (severity == IceCanContinue)
    return;

  /* FIXME: the ICElib docs are completely vague about what we're
   * supposed to do in this case. Need to verify that calling
   * IceCloseConnection() here is guaranteed to cause neither
   * free-memory-reads nor leaks.
   */
  IceCloseConnection (conn);
}

static void
ice_io_error_handler (IceConn conn)
{
  g_debug ("ice_io_error_handler (%p)", conn);

  /* We don't need to do anything here; the next call to
   * IceProcessMessages() for this connection will receive
   * IceProcessMessagesIOError and we can handle the error there.
   */
}

static void
sms_error_handler (SmsConn conn, Bool swap, int offending_minor_opcode,
		   unsigned long offending_sequence_num, int error_class,
		   int severity, IcePointer values)
{
  g_debug ("sms_error_handler (%p, %s, %d, %lx, %d, %d)",
	   conn, swap ? "TRUE" : "FALSE", offending_minor_opcode,
	   offending_sequence_num, error_class, severity);

  /* We don't need to do anything here; if the connection needs to be
   * closed, libSM will do that itself.
   */
}

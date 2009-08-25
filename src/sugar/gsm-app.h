/* gsmapp.h
 * Copyright (C) 2006 Novell, Inc.
 *
 */

#ifndef __GSM_APP_H__
#define __GSM_APP_H__

#include <glib-object.h>
#include <sys/types.h>

#include "eggdesktopfile.h"
#include "gsm-session.h"

G_BEGIN_DECLS

#define GSM_TYPE_APP            (gsm_app_get_type ())
#define GSM_APP(obj)            (G_TYPE_CHECK_INSTANCE_CAST ((obj), GSM_TYPE_APP, GsmApp))
#define GSM_APP_CLASS(klass)    (G_TYPE_CHECK_CLASS_CAST ((klass), GSM_TYPE_APP, GsmAppClass))
#define GSM_IS_APP(obj)         (G_TYPE_CHECK_INSTANCE_TYPE ((obj), GSM_TYPE_APP))
#define GSM_IS_APP_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), GSM_TYPE_APP))
#define GSM_APP_GET_CLASS(obj)  (G_TYPE_INSTANCE_GET_CLASS ((obj), GSM_TYPE_APP, GsmAppClass))

typedef struct _GsmApp        GsmApp;
typedef struct _GsmAppClass   GsmAppClass;
typedef struct _GsmAppPrivate GsmAppPrivate;

struct _GsmApp
{
  GObject parent;

  EggDesktopFile *desktop_file;
  GsmSessionPhase phase;

  pid_t pid;
  char *startup_id, *client_id;
};

struct _GsmAppClass
{
  GObjectClass parent_class;

  /* signals */
  void        (*exited)       (GsmApp *app, int status);
  void        (*registered)   (GsmApp *app);

  /* virtual methods */
  const char *(*get_basename) (GsmApp *app);
  gboolean    (*is_disabled)  (GsmApp *app);
  pid_t       (*launch)       (GsmApp *app, GError **err);
  void        (*set_client)   (GsmApp *app, GsmClient *client);
};

GType            gsm_app_get_type        (void) G_GNUC_CONST;

const char      *gsm_app_get_basename    (GsmApp     *app);
GsmSessionPhase  gsm_app_get_phase       (GsmApp     *app);
gboolean         gsm_app_provides        (GsmApp     *app,
					  const char *service);
gboolean         gsm_app_is_disabled     (GsmApp     *app);
pid_t            gsm_app_launch          (GsmApp     *app,
					  GError    **err);
void             gsm_app_set_client      (GsmApp     *app,
					  GsmClient  *client);

void             gsm_app_registered      (GsmApp     *app);

G_END_DECLS

#endif /* __GSM_APP_H__ */

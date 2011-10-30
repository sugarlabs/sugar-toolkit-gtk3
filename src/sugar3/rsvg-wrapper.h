/* rsvg-wrapper.h
 * Copyright (C) 2011 Raul Gutierrez Segales
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

#ifndef __RSVG_WRAPPER_H__
#define __RSVG_WRAPPER_H__

#include <cairo.h>
#include <glib.h>
#include <glib-object.h>
#include <gdk-pixbuf/gdk-pixbuf.h>

G_BEGIN_DECLS

#define SUGAR_TYPE_RSVG_WRAPPER sugar_rsvg_wrapper_get_type ()

#define SUGAR_RSVG_WRAPPER(obj) \
  (G_TYPE_CHECK_INSTANCE_CAST ((obj), SUGAR_TYPE_RSVG_WRAPPER, SugarRsvgWrapper))

#define SUGAR_RSVG_WRAPPER_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_CAST ((klass), SUGAR_TYPE_RSVG_WRAPPER, SugarRsvgWrapperClass))

#define SUGAR_IS_RSVG_WRAPPER(obj) \
  (G_TYPE_CHECK_INSTANCE_TYPE ((obj), SUGAR_TYPE_RSVG_WRAPPER))

#define SUGAR_IS_RSVG_WRAPPER_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_TYPE ((klass), SUGAR_TYPE_RSVG_WRAPPER))

#define SUGAR_RSVG_WRAPPER_GET_CLASS(obj) \
  (G_TYPE_INSTANCE_GET_CLASS ((obj), SUGAR_TYPE_RSVG_WRAPPER, SugarRsvgWrapperClass))

typedef struct _SugarRsvgWrapper SugarRsvgWrapper;
typedef struct _SugarRsvgWrapperClass SugarRsvgWrapperClass;
typedef struct _SugarRsvgWrapperPrivate SugarRsvgWrapperPrivate;

struct _SugarRsvgWrapper
{
  GObject parent;
  SugarRsvgWrapperPrivate *priv;
};

struct _SugarRsvgWrapperClass
{
  GObjectClass parent_class;
};

GType sugar_rsvg_wrapper_get_type (void);

SugarRsvgWrapper* sugar_rsvg_wrapper_new (const guint8 *data, gsize len);
int sugar_rsvg_wrapper_load(SugarRsvgWrapper *wrapper);
int sugar_rsvg_wrapper_get_width(SugarRsvgWrapper *wrapper);
int sugar_rsvg_wrapper_get_height(SugarRsvgWrapper *wrapper);
void sugar_rsvg_wrapper_render_cairo(SugarRsvgWrapper *wrapper, cairo_t * cr);
GdkPixbuf * sugar_rsvg_wrapper_get_pixbuf(SugarRsvgWrapper *wrapper);

#endif /* __RSVG_WRAPPER_H__ */

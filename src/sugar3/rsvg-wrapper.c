/* rsvg-wrapper.c
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


/* Wrapper around rsvg while it gets introspection support.
 *
 * See: https://bugzilla.gnome.org/show_bug.cgi?id=663049
 */

#include "rsvg-wrapper.h"
#include <librsvg/rsvg.h>
#include <librsvg/rsvg-cairo.h>


G_DEFINE_TYPE (SugarRsvgWrapper, sugar_rsvg_wrapper, G_TYPE_OBJECT)

#define RSVG_WRAPPER_PRIVATE(o) \
  (G_TYPE_INSTANCE_GET_PRIVATE ((o), SUGAR_TYPE_RSVG_WRAPPER, SugarRsvgWrapperPrivate))

struct _SugarRsvgWrapperPrivate
{
  RsvgHandle *handle;
};

static void
sugar_rsvg_wrapper_dispose (GObject *object)
{
  SugarRsvgWrapper *self = SUGAR_RSVG_WRAPPER (object);
  SugarRsvgWrapperPrivate *priv = self->priv;

  if (priv->handle)
    rsvg_handle_free (priv->handle);

  G_OBJECT_CLASS (sugar_rsvg_wrapper_parent_class)->dispose (object);
}

static void
sugar_rsvg_wrapper_class_init (SugarRsvgWrapperClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);

  g_type_class_add_private (klass, sizeof (SugarRsvgWrapperPrivate));

  object_class->dispose = sugar_rsvg_wrapper_dispose;
}

static void
sugar_rsvg_wrapper_init (SugarRsvgWrapper *wrapper)
{
  SugarRsvgWrapperPrivate *priv;

  priv = wrapper->priv = RSVG_WRAPPER_PRIVATE (wrapper);
  priv->handle = NULL;
}


/**
 * sugar_rsvg_wrapper_new:
 * @data: (transfer none) (array length=len): the image data
 * @len: the length of @data
 *
 * Creates a new wrapper object
 *
 * Returns: (transfer full): new #SugarRsvgWrapper
 **/
SugarRsvgWrapper*
sugar_rsvg_wrapper_new (const guint8 *data,
			gsize len)
{
  SugarRsvgWrapper* wrapper = g_object_new (SUGAR_TYPE_RSVG_WRAPPER, NULL);
  SugarRsvgWrapperPrivate *priv;
  GError *error;

  priv = RSVG_WRAPPER_PRIVATE (wrapper);

  /* My code never fails, hence I don't bother checking
   * the error after the call - rgs
   */
  priv->handle = rsvg_handle_new_from_data (data, len, &error);

  return wrapper;
}

/**
 * sugar_rsvg_wrapper_get_width:
 * @wrapper: an #SugarRsvgWrapper
 *
 * Gets the width of the associated RsvgHandle.
 *
 * Returns: The width of the wrapped RsvgHandle
 **/
int sugar_rsvg_wrapper_get_width(SugarRsvgWrapper *wrapper)
{
  SugarRsvgWrapperPrivate *priv = RSVG_WRAPPER_PRIVATE (wrapper);
  RsvgDimensionData dim;

  rsvg_handle_get_dimensions (priv->handle, &dim);
  return dim.width;
}

/**
 * sugar_rsvg_wrapper_get_height:
 * @wrapper: an #SugarRsvgWrapper
 *
 * Gets the height of the associated RsvgHandle.
 *
 * Returns: The height of the wrapped RsvgHandle
 **/
int sugar_rsvg_wrapper_get_height(SugarRsvgWrapper *wrapper)
{
  SugarRsvgWrapperPrivate *priv = RSVG_WRAPPER_PRIVATE (wrapper);
  RsvgDimensionData dim;

  rsvg_handle_get_dimensions (priv->handle, &dim);
  return dim.height;
}

/**
 * sugar_rsvg_wrapper_render_cairo:
 * @wrapper: an #SugarRsvgWrapper
 * @cr: the cairo region
 *
 **/
void sugar_rsvg_wrapper_render_cairo(SugarRsvgWrapper *wrapper, cairo_t * cr)
{
  SugarRsvgWrapperPrivate *priv = RSVG_WRAPPER_PRIVATE (wrapper);
  rsvg_handle_render_cairo (priv->handle, cr);
}

/**
 * sugar_rsvg_wrapper_get_pixbuf:
 * @wrapper: an #SugarRsvgWrapper
 *
 * Returns: (transfer full): the #GdkPixbuf
 **/
GdkPixbuf *sugar_rsvg_wrapper_get_pixbuf(SugarRsvgWrapper *wrapper)
{
  SugarRsvgWrapperPrivate *priv = RSVG_WRAPPER_PRIVATE (wrapper);
  return rsvg_handle_get_pixbuf (priv->handle);
}

/* gdk-wrapper.c
 *
 * Copyright (C) 1995-2007 Peter Mattis, Spencer Kimball,
 *                         Josh MacDonald, Ryan Lortie
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

/* Work around introspection unfriendly API in gdk */

#include "gdk-wrapper.h"
#include <string.h>

/**
 * gdk_wrapper_property_change:
 * @window: a #GdkWindow
 * @property: the property to change
 * @type: the new type for the property. If @mode is
 *   %GDK_PROP_MODE_PREPEND or %GDK_PROP_MODE_APPEND, then this
 *   must match the existing type or an error will occur.
 * @format: the new format for the property. If @mode is
 *   %GDK_PROP_MODE_PREPEND or %GDK_PROP_MODE_APPEND, then this
 *   must match the existing format or an error will occur.
 * @mode: a value describing how the new data is to be combined
 *   with the current data.
 * @data: the data (a <literal>gchar *</literal>)
 *
 * Changes the contents of a property on a window.
 */
void
gdk_wrapper_property_change (GdkWindow    *window,
			     const gchar  *property,
			     const gchar  *type,
			     gint          format,
			     GdkPropMode   mode,
			     const gchar  *data)
{
  GdkAtom property_a = gdk_atom_intern (property, FALSE);
  GdkAtom type_a = gdk_atom_intern (type, FALSE);
  gint nelements = strlen(data);

  gdk_property_change (window, property_a, type_a, format, mode,(const guchar *)data,
		       nelements);
}


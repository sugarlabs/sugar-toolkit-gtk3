/* gdk-wrapper.h
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

#ifndef __GDK_WRAPPER_H__
#define __GDK_WRAPPER_H__

#include <gdk/gdk.h>



void
gdk_wrapper_property_change (GdkWindow    *window,
			     const gchar  *property,
			     const gchar  *type,
			     gint          format,
			     GdkPropMode   mode,
			     const gchar *data);


#endif /* __GDK_WRAPPER_H__ */

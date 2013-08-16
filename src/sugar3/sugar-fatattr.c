/*
 * Copyright (C) 2013, Walter Bender
 * Copyright (C) 2009 Aaron Stone <aaron@serendipity.cx>
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
 */

// Gives us O_NOATIME
#define _GNU_SOURCE

#include <sys/types.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <linux/msdos_fs.h>

#include <glib.h>

#include <errno.h>
#include <stdio.h>
#include <string.h>

// This function is wrapped by getattrs/setattrs
static int _ioctl_attrs(char *file, __u32 *attrs, int ioctlnum, char *verb)
{
    int fd;

    // Interesting, we don't need a read-write handle to call the SET ioctl.
    fd = open(file, O_RDONLY | O_NOATIME);
    if (fd < 0) {
        fprintf(stderr, "Error opening '%s': %s\n", file, strerror(errno));
        goto err;
    }

    if (ioctl(fd, ioctlnum, attrs) != 0) {
        fprintf(stderr, "Error %s attributes: %s\n", verb, strerror(errno));
        goto err;
    }

    close (fd);
    return 0;

    err:
        close (fd);
        return -1;
}

static int getattrs(char *file, __u32 *attrs)
{
    return _ioctl_attrs(file, attrs, FAT_IOCTL_GET_ATTRIBUTES, "reading");
}

static int setattrs(char *file, __u32 *attrs)
{
    return _ioctl_attrs(file, attrs, FAT_IOCTL_SET_ATTRIBUTES, "writing");
}

static int set_hidden_attrib(char *pathname)
{
    __u32 attrs = 0;
    char *file = NULL;

    file = pathname;
    if (getattrs(file, &attrs) == 0) {
        attrs |= ATTR_HIDDEN;
        setattrs(file, &attrs);
        return 0;
    }

    return -1;
}

/**
 * Set the FAT HIDDEN attribute.
 *
 * sugar_fat_set_hidden_attrib: 
 * @const char: (file utf8)
 */
gboolean sugar_fat_set_hidden_attrib(const char *file)
{
    if (set_hidden_attrib(file) == 0) {
        return TRUE;
    }
    return FALSE;
}

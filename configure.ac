AC_INIT([sugar-toolkit-gtk3],[0.101.5],[],[sugar-toolkit-gtk3])

AC_PREREQ([2.59])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([configure.ac])

AM_INIT_AUTOMAKE([1.9 foreign dist-xz no-dist-gzip])

AM_MAINTAINER_MODE
AC_DISABLE_STATIC
AC_PROG_LIBTOOL

GNOME_COMPILE_WARNINGS(maximum)

AC_PATH_PROG([GLIB_GENMARSHAL], [glib-genmarshal])

PYTHON=python2
AM_PATH_PYTHON

PKG_CHECK_MODULES(EXT, gtk+-3.0 gdk-3.0 gdk-pixbuf-2.0 sm ice alsa
                       librsvg-2.0 xfixes xi x11)

GLIB_MKENUMS=`$PKG_CONFIG glib-2.0 --variable=glib_mkenums`
AC_SUBST(GLIB_MKENUMS)

IT_PROG_INTLTOOL([0.35.0])
GETTEXT_PACKAGE=sugar-toolkit-gtk3
AC_SUBST([GETTEXT_PACKAGE])
AM_GLIB_GNU_GETTEXT

GOBJECT_INTROSPECTION_REQUIRE([1.30.0])

AC_OUTPUT([
Makefile
bin/Makefile
src/Makefile
src/sugar3/Makefile
src/sugar3/activity/Makefile
src/sugar3/bundle/Makefile
src/sugar3/graphics/Makefile
src/sugar3/event-controller/Makefile
src/sugar3/presence/Makefile
src/sugar3/datastore/Makefile
src/sugar3/dispatch/Makefile
src/sugar3/test/Makefile
src/sugar3/config.py
po/Makefile.in
])

AC_INIT([sugar-toolkit-gtk3],[0.121],[],[sugar-toolkit-gtk3])

AC_PREREQ([2.71])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([configure.ac])

AM_INIT_AUTOMAKE([1.9 foreign dist-xz no-dist-gzip])

AM_MAINTAINER_MODE
AC_DISABLE_STATIC
LT_INIT

GNOME_COMPILE_WARNINGS(maximum)

AC_PATH_PROG([GLIB_GENMARSHAL], [glib-genmarshal])

AC_ARG_WITH([python2],
        AS_HELP_STRING([--with-python2], [build for Python 2]),
        [with_python3=no], [with_python2=unset])

AC_ARG_WITH([python3],
        AS_HELP_STRING([--with-python3], [build for Python 3 (default)]),
        [], [with_python3=unset])

AS_IF([test "x$with_python3" != xno],
	[AM_PATH_PYTHON([3])],
	[AS_IF([test "x$with_python2" = xyes], [AM_PATH_PYTHON([2.7])],)])

PKG_CHECK_MODULES(EXT, gtk+-3.0 gdk-3.0 gdk-pixbuf-2.0 sm ice alsa
                       librsvg-2.0 xfixes xi x11)

GLIB_MKENUMS=`$PKG_CONFIG glib-2.0 --variable=glib_mkenums`
AC_SUBST(GLIB_MKENUMS)

IT_PROG_INTLTOOL([0.35.0])
GETTEXT_PACKAGE=sugar-toolkit-gtk3
AC_SUBST([GETTEXT_PACKAGE])
AM_GLIB_GNU_GETTEXT

GOBJECT_INTROSPECTION_REQUIRE([1.30.0])

AC_CONFIG_FILES([
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
AC_OUTPUT

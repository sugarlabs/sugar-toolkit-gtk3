AC_INIT([sugar-toolkit-gtk3],[0.95.1],[],[sugar-toolkit-gtk3])

AC_PREREQ([2.59])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([configure.ac])

AM_INIT_AUTOMAKE([1.9 foreign dist-bzip2 no-dist-gzip])

AM_MAINTAINER_MODE
AC_DISABLE_STATIC
AC_PROG_LIBTOOL

GNOME_COMPILE_WARNINGS(maximum)

AC_PATH_PROG([GLIB_GENMARSHAL], [glib-genmarshal])

AM_PATH_PYTHON
AM_CHECK_PYTHON_HEADERS(,[AC_MSG_ERROR(could not find Python headers)])

AC_PATH_PROG(PYGTK_CODEGEN, pygtk-codegen-2.0, no)

PKG_CHECK_MODULES(EXT, gtk+-3.0 gdk-3.0 gdk-pixbuf-2.0 sm ice alsa)

PYGTK_DEFSDIR=`$PKG_CONFIG --variable=defsdir pygtk-2.0`
AC_SUBST(PYGTK_DEFSDIR)

# Setup GETTEXT
#
ALL_LINGUAS="af am ar ay bg bi bn_IN bn ca cpp cs da de dz el en es fa_AF fa ff fil fr gu ha he hi ht hu id ig is it ja km ko kos mg mi mk ml mn mr ms mvo nb ne nl pa pap pis pl ps pt_BR pt qu ro ru rw sd si sk sl sq sv sw ta te th tpi tr tvl tzo ug ur vi wa yo zh_CN zh_TW"

GETTEXT_PACKAGE=sugar-toolkit
AC_PROG_INTLTOOL([0.33])
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [Gettext package])
AM_GLIB_GNU_GETTEXT

GOBJECT_INTROSPECTION_CHECK([1.30.0])

AC_OUTPUT([
Makefile
src/Makefile
src/sugar3/Makefile
src/sugar3/activity/Makefile
src/sugar3/bundle/Makefile
src/sugar3/graphics/Makefile
src/sugar3/presence/Makefile
src/sugar3/datastore/Makefile
po/Makefile.in
])

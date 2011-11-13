SUBDIRS = activity bundle graphics presence datastore

sugardir = $(pythondir)/sugar3
sugar_PYTHON =		\
	env.py		\
        network.py	\
	profile.py	\
	session.py	\
	util.py		\
	wm.py

lib_LTLIBRARIES = libsugarext.la

libsugarext_la_CFLAGS = 		\
	-DHAVE_ALSA		\
	$(EXT_CFLAGS)	\
	$(WARN_CFLAGS)

libsugarext_la_LDFLAGS = $(LDADD)
libsugarext_la_LIBADD = $(EXT_LIBS) -lSM -lICE -lasound

libsugarext_la_SOURCES =		\
	$(BUILT_SOURCES)		\
	acme-volume-alsa.c		\
	acme-volume-alsa.h		\
	acme-volume.c			\
	acme-volume.h			\
	eggaccelerators.c		\
	eggaccelerators.h		\
	eggdesktopfile.c		\
	eggdesktopfile.h		\
	eggsmclient.c			\
	eggsmclient.h			\
	eggsmclient-private.h		\
	eggsmclient-xsmp.c		\
	gsm-app.c			\
	gsm-app.h			\
	gsm-client.c			\
	gsm-client.h			\
	gsm-client-xsmp.c		\
	gsm-client-xsmp.h		\
	gsm-session.c			\
	gsm-session.h			\
	gsm-xsmp.c			\
	gsm-xsmp.h			\
	sugar-grid.c			\
	sugar-grid.h			\
	sugar-key-grabber.c		\
	sugar-key-grabber.h		\
	sugar-menu.c			\
	sugar-menu.h

BUILT_SOURCES = 			\
	sugar-marshal.c			\
	sugar-marshal.h

sugar-marshal.c: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal \
		$(srcdir)/sugar-marshal.list --header --body > sugar-marshal.c

sugar-marshal.h: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal \
		$(srcdir)/sugar-marshal.list --header > sugar-marshal.h

CLEANFILES = $(BUILT_SOURCES)
EXTRA_DIST = sugar-marshal.list

-include $(INTROSPECTION_MAKEFILE)
INTROSPECTION_GIRS = SugarExt-1.0.gir
INTROSPECTION_SCANNER_ARGS = --identifier-prefix=Sugar --symbol-prefix=sugar \
	--identifier-prefix=EggSM --symbol-prefix=egg_sm \
	--identifier-prefix=Gsm --symbol-prefix=gsm \
	--identifier-prefix=Acme --symbol-prefix=acme
SugarExt_1_0_gir_LIBS = libsugarext.la
SugarExt_1_0_gir_FILES = \
	acme-volume.c \
	acme-volume.h \
	acme-volume-alsa.c \
	acme-volume-alsa.h \
	eggsmclient.c \
	eggsmclient.h \
	gsm-session.c \
	gsm-session.h \
	gsm-xsmp.c \
	gsm-xsmp.h \
	sugar-key-grabber.c \
	sugar-key-grabber.h
SugarExt_1_0_gir_INCLUDES = Gtk-3.0 Gdk-3.0
SugarExt_1_0_gir_PACKAGES = gtk+-3.0 gdk-3.0
SugarExt_1_0_gir_EXPORT_PACKAGES = SugarExt-1.0

girdir = $(datadir)/gir-1.0
gir_DATA = SugarExt-1.0.gir

typelibdir = $(libdir)/girepository-1.0
typelib_DATA = SugarExt-1.0.typelib

CLEANFILES += $(gir_DATA) $(typelib_DATA)

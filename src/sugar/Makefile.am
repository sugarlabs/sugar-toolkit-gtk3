SUBDIRS = activity bundle graphics presence datastore

sugardir = $(pythondir)/sugar
sugar_PYTHON =		\
	env.py		\
        network.py	\
	profile.py	\
	session.py	\
	util.py		\
	wm.py

pkgpyexecdir = $(pythondir)/sugar

pkgpyexec_LTLIBRARIES = _sugarext.la

_sugarext_la_CFLAGS = 		\
	-DHAVE_ALSA		\
        $(WARN_CFLAGS)		\
	$(EXT_CFLAGS)		\
	$(PYTHON_INCLUDES)

_sugarext_la_LDFLAGS = -module -avoid-version
_sugarext_la_LIBADD = $(EXT_LIBS) -lSM -lICE

_sugarext_la_SOURCES =			\
	$(BUILT_SOURCES)		\
	_sugarextmodule.c		\
	acme-volume.h			\
	acme-volume.c			\
	acme-volume-alsa.h		\
	acme-volume-alsa.c		\
        gsm-app.h			\
	gsm-app.c			\
	gsm-client.h			\
	gsm-client.c			\
	gsm-client-xsmp.h		\
	gsm-client-xsmp.c		\
	gsm-xsmp.h			\
	gsm-xsmp.c			\
	gsm-session.h			\
	gsm-session.c			\
	eggaccelerators.c		\
	eggaccelerators.h		\
	eggdesktopfile.h		\
	eggdesktopfile.c		\
	eggsmclient.h			\
	eggsmclient.c			\
	eggsmclient-private.h		\
	eggsmclient-xsmp.c		\
	sugar-grid.c			\
	sugar-grid.h			\
	sugar-key-grabber.c		\
	sugar-key-grabber.h		\
	sugar-menu.h			\
	sugar-menu.c

BUILT_SOURCES = 			\
	_sugarext.c			\
	sugar-marshal.c			\
	sugar-marshal.h

_sugarext.c: _sugarext.defs _sugarext.override

.defs.c:
	(cd $(srcdir)\
	 && $(PYGTK_CODEGEN) \
	    --register $(PYGTK_DEFSDIR)/gdk-types.defs \
	    --register $(PYGTK_DEFSDIR)/gtk-types.defs \
	    --override $*.override \
	    --prefix py$* $*.defs) > gen-$*.c \
	&& cp gen-$*.c $*.c \
	&& rm -f gen-$*.c

sugar-marshal.c: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal \
		$(srcdir)/sugar-marshal.list --header --body > sugar-marshal.c

sugar-marshal.h: sugar-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_marshal \
		$(srcdir)/sugar-marshal.list --header > sugar-marshal.h

CLEANFILES = $(BUILT_SOURCES)
EXTRA_DIST = sugar-marshal.list _sugarext.defs _sugarext.override

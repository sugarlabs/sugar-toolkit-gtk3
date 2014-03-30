ACLOCAL_AMFLAGS = -I m4
DISTCHECK_CONFIGURE_FLAGS = --enable-introspection

DISTCLEANFILES =		\
	intltool-extract	\
	intltool-merge		\
	intltool-update

EXTRA_DIST =                    \
	intltool-merge.in       \
	intltool-update.in      \
	intltool-extract.in

SUBDIRS = bin src po

check-po:
	@for i in $(top_srcdir)/po/*.po ; do \
        if ! grep -q ^`basename $$i | \
        sed 's,.po,,'`$$ $(top_srcdir)/po/LINGUAS ; then \
            echo '***' `basename $$i | \
            sed 's,.po,,'` missing from po/LINGUAS '***' ; \
            exit 1; \
        fi; \
    done;

test: check-po
	pyflakes $(top_srcdir)
	pep8 $(top_srcdir)
	python -m sugar3.test.discover $(top_srcdir)/tests

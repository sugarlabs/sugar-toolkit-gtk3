ACLOCAL_AMFLAGS = -I m4
DISTCHECK_CONFIGURE_FLAGS = --enable-introspection

TESTS_TMPDIR=$(abs_builddir)/tests-tmp
TESTS_PYTHONPATH=$(abs_srcdir)/src:$(PYTHONPATH)

DISTCLEANFILES =		\
	intltool-extract	\
	intltool-merge		\
	intltool-update

EXTRA_DIST =                    \
	intltool-merge.in       \
	intltool-update.in      \
	intltool-extract.in

SUBDIRS = bin src po

check: test
	pyflakes $(top_srcdir)

test:
	mkdir -p $(TESTS_TMPDIR)
	cd $(top_srcdir)/tests; \
	TMPDIR=$(TESTS_TMPDIR) PYTHONPATH=$(TESTS_PYTHONPATH) \
	python -m unittest discover; \
	status=$$?; \
	rm -rf $(TESTS_TMPDIR); \
	exit $$status

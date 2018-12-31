ifneq ($(wildcard Makefile.local),)
include Makefile.local
endif

PYTHON ?= python

ifneq ($(PREFIX),)
install_args = --prefix=$(PREFIX)
endif

default:
	$(PYTHON) setup.py build

install: default
	$(PYTHON) setup.py install $(install_args)

develop:
	$(PYTHON) setup.py develop --user

bundle:
	git archive HEAD --format=tar --prefix=ocs/ | gzip -c > ocs.tar.gz


.dummy: default install

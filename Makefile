ifneq ($(wildcard Makefile.local),)
include Makefile.local
endif

PYTHON ?= python
VERSION := $(shell python -c 'import ocs; print (ocs.__version__.replace("+", "-"))')

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

docker-image:
	docker build -t ocs:$(VERSION) .
	docker tag ocs:$(VERSION) ocs:latest

.dummy: default install

# vim: set expandtab!:

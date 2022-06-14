SITE_ARGS = --site-file default.yaml
OCSLOCAL = ocs-local-support $(SITE_ARGS)
PYTHON ?= python

default:
	echo Your options are prepare,up,run,down,cleanup.

prepare:
	-mkdir dot_crossbar
	-mkdir logs
	-mkdir data
	$(OCSLOCAL) generate_crossbar_config

up:
	$(OCSLOCAL) start

run:
	$(PYTHON) run_acq.py $(SITE_ARGS)

down:
	-$(OCSLOCAL) stop

cleanup:
	-rm -r dot_crossbar logs data __pycache__

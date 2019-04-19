SITE_ARGS = --site-file default.yaml
OCSBOW = ocsbow $(SITE_ARGS)
PYTHON ?= python

default:
	echo Your options are prepare,up,run,down,cleanup.

prepare:
	-mkdir dot_crossbar
	-mkdir logs
	-mkdir data
	$(OCSBOW) crossbar generate_config

up:
	$(OCSBOW) up

run:
	$(PYTHON) run_acq.py $(SITE_ARGS)

down:
	-$(OCSBOW) down

cleanup:
	-rm -r dot_crossbar logs data __pycache__

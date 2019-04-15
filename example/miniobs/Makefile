SITE_ARGS = --site-file default.yaml
OCSBOW = ocsbow $(SITE_ARGS)
PYTHON ?= python

default:
	echo Your options are prepare,up,run,down,cleanup.

prepare:
	-mkdir dot_crossbar
	-mkdir logs
	-mkdir data
	$(OCSBOW) crossbar generate_config > dot_crossbar/config.json

up:
	$(OCSBOW) crossbar start
	$(OCSBOW) hostmaster start
	$(OCSBOW) agent start

run:
	$(PYTHON) run_acq.py $(SITE_ARGS)

down:
	-$(OCSBOW) agent stop
	-$(OCSBOW) hostmaster stop
	-$(OCSBOW) crossbar stop

cleanup:
	-rm -r dot_crossbar logs data __pycache__

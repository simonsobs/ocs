# If you need to override python or crossbar paths, edit the variables
# below, or invoke make like this, e.g.:
#
#   PYTHON=python2  make run_client
#

PYTHON ?= python3
CROSSBAR ?= crossbar

# Specify the site configuration file.  Also override the host name.
SITE_ARGS ?= --site-file telescope.yaml --site-host host-1

default:
	@echo
	@echo -n "This Makefile is for launching the example.  "
	@echo "In three separate terminals run:"
	@echo
	@echo "  make run_crossbar"
	@echo "  make run_agent"
	@echo "  make run_client"
	@echo

run_crossbar:
	$(CROSSBAR) start --cbdir dot_crossbar/

run_agent:
	$(PYTHON) example_agent.py $(SITE_ARGS) --instance-id=thermo1

run_client:
	$(PYTHON) example_ctrl.py $(SITE_ARGS)

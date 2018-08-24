.. highlight:: rst

.. _lakeshore372:

=============
Lakeshore 372
=============

The Lakeshore 372 (LS372) units are used for 100 mK and 1K thermometer readout.
Basic functionality to interface and control an LS372 is provided by the
``ocs.Lakeshore.Lakeshore372.py`` module.

For the API all methods should start with one of the following:

    * set - set a parameter of arbitary input (i.e. set_excitation)
    * get - get the status of a parameter (i.e. get_excitation)
    * enable - enable a boolean parameter (i.e. enable_autoscan)
    * disable - disbale a boolean parameter (i.e. disable_channel)

API
---
.. automodule:: ocs.Lakeshore.Lakeshore372
    :members:

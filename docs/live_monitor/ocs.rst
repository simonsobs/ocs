.. highlight:: rst

Running OCS Clients
===================

All the OCS Agents should now be running in Docker containers. To command them
we run an OCS Client. Examples of OCS Clients can be found in the
`ocs/clients`_ directory. As an example, we can start data acquisition on a
Lakeshore using ``ocs/clients/start_new_therm.py``::

    $ python3 start_new_therm.py --target=LSA23JD
    2019-01-10T11:53:52-0500 transport connected
    2019-01-10T11:53:52-0500 session joined: SessionDetails(realm=<test_realm>, session=1042697241527250, authid=<GJJU-4YG3-3UCG-CSMJ-TQTW-PWSM>, authrole=<server>, authmethod=anonymous, authprovider=static, authextra=None, resumed=None, resumable=None, resume_token=None)
    2019-01-10T11:53:52-0500 Entered control
    2019-01-10T11:53:52-0500 Registering tasks
    2019-01-10T11:53:52-0500 Starting Aggregator
    2019-01-10T11:53:52-0500 Starting Data Acquisition

Once you have started data collection, the data is being acquired by the
Lakeshore Agent and published over the crossbar server to the Aggregator Agent.
There it is being written to disk at the location you have configured
(`/data` in our example). The data is also passed to the live monitor, where it
can be displayed in Grafana. We still discuss configuring Grafana in the next
section.

.. _ocs/clients: https://github.com/simonsobs/ocs/tree/master/clients

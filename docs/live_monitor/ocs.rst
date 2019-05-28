.. highlight:: rst

Running the OCS Agents and Clients
==================================

Now that the live monitor is configured we can setup our OCS Agents which
communicate with our hardware and save the data to disk. This will involve at
least three Agents. For our example we will run the RegistryAgent, the data
Aggregator, and an LS372 Agent. 

.. note::
    An Agent for managing the running and startup of all these Agents is
    currently in the works, though is not quite ready yet. When done it will
    eliminate the need to start these individually. Bear with us for now.

We'll run these from within the OCS repo we cloned earlier, so navigate there.
The Agents are located within the aptly named ``agents/`` directory.

First, the RegistryAgent. To start we can just run the ``registry.py`` file::

    $ python3 registry.py
    2019-01-10T11:42:46-0500 transport connected
    2019-01-10T11:42:46-0500 session joined: SessionDetails(realm=<test_realm>, session=6826665888645921, authid=<FNRP-LLQG-AGY3-KXJ4-PJKT-ESYA>, authrole=<server>, authmethod=anonymous, authprovider=static, authextra=None, resumed=None, resumable=None, resume_token=None)
    2019-01-10T11:42:46-0500 start called for register_agent
    2019-01-10T11:42:46-0500 register_agent:0 Status is now "starting".
    2019-01-10T11:42:46-0500 Registered agent observatory.registry
    2019-01-10T11:42:46-0500 register_agent:0 Registered agent observatory.registry
    2019-01-10T11:42:46-0500 register_agent:0 Registered agent observatory.registry
    2019-01-10T11:42:46-0500 register_agent:0 Status is now "done".

Next the Aggregator Agent::

    $ python3 aggregator_agent.py
    2018-11-01T18:17:19-0400 transport connected
    2018-11-01T18:17:19-0400 session joined: SessionDetails(realm=<test_realm>, session=3951407465670067, authid=<PEL3-C365-75XL-KQUX-A9HK-UXA7>, authrole=<server>, authmethod=anonymous, authprovider=static, authextra=None, resumed=None, resumable=None, resume_token=None)

Finally, the LS372 Agent. Note we specify the ``instance-id`` as configured in
our YAML file::

    $ python3 LS372_agent.py --instance-id=LSA23JD
    site_config is setting values of "serial_number" to "LSA23JD".
    site_config is setting values of "ip_address" to "10.10.10.6".
    I am in charge of device with serial number: LSA23JD
    2019-01-10T11:52:06-0500 transport connected
    2019-01-10T11:52:06-0500 session joined: SessionDetails(realm=<test_realm>, session=122770728011642, authid=<AW34-LK5L-CQGA-N9RP-QTYE-VUMQ>, authrole=<server>, authmethod=anonymous, authprovider=static, authextra=None, resumed=None, resumable=None, resume_token=None)

Now we are ready to run an OCS Client which commands the agents to begin data
aggregation and data acquisition for this we will run ``clients/therm_and_agg_ctrl.py``::

    $ python3 therm_and_agg_ctrl.py --target=LSA23JD
    2019-01-10T11:53:52-0500 transport connected
    2019-01-10T11:53:52-0500 session joined: SessionDetails(realm=<test_realm>, session=1042697241527250, authid=<GJJU-4YG3-3UCG-CSMJ-TQTW-PWSM>, authrole=<server>, authmethod=anonymous, authprovider=static, authextra=None, resumed=None, resumable=None, resume_token=None)
    2019-01-10T11:53:52-0500 Entered control
    2019-01-10T11:53:52-0500 Registering tasks
    2019-01-10T11:53:52-0500 Starting Aggregator
    2019-01-10T11:53:52-0500 Starting Data Acquisition

Data should now be displaying the terminal you started the LS372 Agent in, and
file output should be occurring in the configured Data Aggregator directory,
which the Agent reports.

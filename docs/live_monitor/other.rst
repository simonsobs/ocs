.. highlight:: rst

Other Info
==========

Grafana
-------

The ``grafana-storage`` volume that we initialized will allow for 
persistent storage in the event the container is rebuilt. Dashboards can also
be backed up by exporting them to a ``.json`` file.

.. warning::
    This should be a one time setup, however, if you destroy the
    grafana-storage volume you will lose your configuration. We encourage you
    to export your favorite dashboards for backup.

Backing up Panels
``````````````````

Networking
----------

.. _firewall:

Configuring a Firewall
``````````````````````

.. note::
    This problem is solved in part by the explicit exposure of the crossbar
    server port to localhost in our ``docker-compose.yml`` file in the line
    ``ports: "127.0.0.1:3000:3000"``. This ensures port 3000 is only available
    to the localhost. If this is not done (i.e. "ports: 3000:3000") Docker will
    manipulate the iptables to make port 3000 available anywhere, so if your
    computer is publicly facing anyone online can (and will) try to connect.
    This will be evident in your crossbar container's logs.

    That said, the firewall setup is not totally necessary, though still is
    good practice, so I will leave this information here.

If you have convinced your university IT department to allow you to have a
Linux machine on the public network we should take some precautions to secure
the crossbar server, which currently for OCS does not have a secure
authentication mechanism, from the outside world. The simplest way of doing so
is by setting up a firewall.

Ubuntu should come with (or have easily installable) a simple front end for
iptables called ufw (Uncomplicated Firewall). This is disabled by default.
Before configuring you should consider any software running on the machine
which may require an open port. We will configure it to have ports 22 and 3000
open, for ssh and Grafana, respectively.

``ufw`` should be disabled by default::

    $ sudo ufw status
    Status: inactive

You can get a list of applications which ``ufw`` knows about with::

    $ sudo ufw app list
    Available applications:
      CUPS
      OpenSSH

We can then allow the ssh port with::

    $ sudo ufw allow OpenSSH
    Rules updated
    Rules updated (v6)

This opens port 22. And finally, we can allow Grafana's port 3000::

    $ sudo ufw allow 3000
    Rules updated
    Rules updated (v6)

Lastly we have to enable ``ufw``::

    $ sudo ufw enable
    Command may disrupt existing ssh connections. Proceed with operation (y|n)? y
    Firewall is active and enabled on system startup

You should then see that the firewall is active::

    $ sudo ufw status
    Status: active

    To                         Action      From
    --                         ------      ----
    OpenSSH                    ALLOW       Anywhere
    3000                       ALLOW       Anywhere
    OpenSSH (v6)               ALLOW       Anywhere (v6)
    3000 (v6)                  ALLOW       Anywhere (v6)

.. _port_forwarding:

Port Forwarding to View Remotely
`````````````````````````````````

If the computer you are running Grafana on is not exposed to the internet you
can still access the web interface if you forward port 3000 to your computer.

You will need a way to ssh to the computer you are running on, so hopefully
there is a gateway machine. To make this easier you should add some lines to
your ``.ssh/config``::

    Host gateway
        HostName gateway.ip.address.or.url
        User username

    Host grafana
        HostName ip.address.of.grafana.computer.on.its.network
        User username
        ProxyCommand ssh gateway -W %h:%p

Here you should replace "gateway" and "grafana" with whatever you want, but
note the two locations for "gateway", namely the second in the ProxyCommand.
This will then allow you to ssh through the gateway to "grafana" with a single
command.

You can then forward the appropriate ports by running::

    $ ssh -N -L 3000:localhost:3000 <grafana computer>

You should now be able to access the grafana interface on your computer by
navigating your browser to ``localhost:3000``.

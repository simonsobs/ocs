.. highlight:: rst

Configuration
=============

We've now installed all the required software. Our next step is to properly
configure the OCS and sisock environments. To organize and version control each
institution/site's configuration we have made the ocs-site-config_ repository.
We will clone this repository and use the example templates as a starting point
for our new site::

    $ git clone https://github.com/simonsobs/ocs-site-configs.git

We'll first want to copy the templates directory and name it for our site (i.e.
``yale``)::

    $ cp -r templates/ yale/

Then we need to setup the TLS certificates for the crossbar server, to do this
a script called ``setup-tls.sh`` is provided, simply enter your new directory
and run it (swap ``yale`` for your institution)::

    $ cd yale/
    $ ./setup-tls.sh

This will generate the required certificates and put them in a directory called
``.crossbar/`` (which already existed in the copied template directory). Next
we need to configure both the OCS and sisock configuration files. These
configurations will differ based on the requirements at each institution.

.. _ocs-site-config: https://github.com/simonsobs/ocs-site-configs

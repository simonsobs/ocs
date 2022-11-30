.. _documentation:

Documentation
-------------

Documentation is important for users writing OCSClients that can interact with
your new Agent. When writing a new Agent you must document the Tasks and
Processes with appropriate docstrings. Additionally a page must be created
within the docs to describe the Agent and provide other key information such as
configuration file examples. You should aim to be a thorough as possible when
writing documentation for your Agent.

Task and Process Documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Each Task and Process within an Agent must be accompanied by a docstring. Here
is a complete example of a well documented Task (or Process)::

    @ocs_agent.param('arg1', type=bool)
    @ocs_agent.param('arg2', default=7, type=int)
    def demo(self, session, params):
        """demo(arg1=None, arg2=7)

        **Task** (or **Process**) - An example task docstring for illustration purposes.

        Parameters:
            arg1 (bool): Useful argument 1.
            arg2 (int, optional): Useful argument 2, defaults to 7. For details see
                                 :func:`socs.agent.demo_agent.DemoClass.detailing_method`

        Examples:
            Example for calling in a client::

                client.demo(arg1=False, arg2=5)

        Notes:
            An example of the session data::

                >>> response.session['data']
                {"fields":
                    {"Channel_05": {"T": 293.644, "R": 33.752, "timestamp": 1601924482.722671},
                     "Channel_06": {"T": 0, "R": 1022.44, "timestamp": 1601924499.5258765},
                     "Channel_08": {"T": 0, "R": 1026.98, "timestamp": 1601924494.8172355},
                     "Channel_01": {"T": 293.41, "R": 108.093, "timestamp": 1601924450.9315426},
                     "Channel_02": {"T": 293.701, "R": 30.7398, "timestamp": 1601924466.6130798}
                    }
                }
        """
        pass

Keep reading for more details on what's going on in this example.

Overriding the Method Signature
```````````````````````````````
``session`` and ``params`` are both required parameters when writing an OCS
Task or Process, but both should be hidden from users writing OCSClients. When
documenting a Task or Process, the method signature should be overridden to
remove both ``session`` and ``params``, and to include any parameters your Task
or Process might take. This is done in the first line of the docstring, by
writing the method name, followed by the parameters in parentheses. In the
above example that looks like::

  def demo(self, session, params=None):
      """demo(arg1=None, arg2=7)"""

This will render the method description as ``delay_task(arg1=None,
arg2=7)`` within Sphinx, rather than ``delay_task(session, params=None)``. The
default values should be put in this documentation. If a parameter is required,
set the param to ``None`` in the method signature. For more info on the
``@ocs_agent.param`` decorator see :ref:`param`.

Keyword Arguments
`````````````````
Internal to OCS the keyword arguments provided to an OCSClient are passed as a
`dict` to ``params``. For the benefit of the end user, these keyword arguments
should be documented in the Agent as if passed as such. So the docstring should
look like::

    Parameters:
        arg1 (bool): Useful argument 1.
        arg2 (int, optional): Useful argument 2, defaults to 7. For details see
                             :func:`socs.agent.lakeshore.LakeshoreClass.the_method`

Examples
````````
Examples should be given using the "Examples" heading when it would improve the
clarity of how to interact with a given Task or Process::

        Examples:
            Example for calling in a client::

                client.demo(arg1=False, arg2=5)

Session Data
````````````
The ``session.data`` object structure is left up to the Agent author. As such,
it needs to be documented so that OCSClient authors know what to expect. If
your Task or Process makes use of ``session.data``, provide an example of the
structure under the "Notes" heading. On the OCSClient end, this
``session.data`` object is returned in the response under
``response.session['data']``. This is how it should be presented in the example
docstrings::

    Notes:
        An example of the session data::

            >>> response.session['data']
            {"fields":
                {"Channel_05": {"T": 293.644, "R": 33.752, "timestamp": 1601924482.722671},
                 "Channel_06": {"T": 0, "R": 1022.44, "timestamp": 1601924499.5258765},
                 "Channel_08": {"T": 0, "R": 1026.98, "timestamp": 1601924494.8172355},
                 "Channel_01": {"T": 293.41, "R": 108.093, "timestamp": 1601924450.9315426},
                 "Channel_02": {"T": 293.701, "R": 30.7398, "timestamp": 1601924466.6130798}
                }
            }

For more details on the ``session.data`` object see :ref:`session_data`.

Agent Reference Pages
^^^^^^^^^^^^^^^^^^^^^
Now that you have documented your Agent's Tasks and Processes appropriately we
need to make the page that will display that documentation. Agent reference
pages are kept in `ocs/docs/agents/
<https://github.com/simonsobs/ocs/tree/main/docs/agents>`_. Each Agent has a
separate `.rst` file.  Each Agent reference page must contain:

* Brief description of the Agent
* Example ocs-site-config configuration block
* Example docker-compose configuration block (if Agent is dockerized)
* Agent API reference

Reference pages can also include:

* Detailed description of Agent or related material
* Example client scripts
* Supporting APIs

Here is a template for an Agent documentation page. Text starting with a '#' is
there to guide you in writing the page and should be replaced or removed.
Unneeded sections should be removed.

.. include:: ../../../example/docs/agent_template.rst
    :code: rst

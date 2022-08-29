Writing Plugins
===============

OCS supports adding external Agents via a plugin system. The underlying
mechanism uses the package metadata, as described in the `PyPA Documentation
<https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/#using-package-metadata>`_.
Making a package into an ocs plugin requires the creation of a plugin file,
which tells OCS how to import new Agents, as well as the addition of an
entry point in the package's ``setup.py`` file.

Plugin File
-----------

The plugin file can be added anywhere in the package, i.e. ``<package>.plugin``.
The contents are simple, just a single string with the name of the package and
a dict with an entry for each Agent describing the module and its entry point.
For example here is the plugin file for the core ocs repository:

.. literalinclude:: ../../ocs/plugin.py
    :language: python

The keys of the agents dictionary should match the names of the Agents set in
the Agent and used in the SCF.

.. warning::
    Conflicting Agent names are not handled well across plugins. Use a unique
    Agent name when adding new Agents until this is improved.

Note that each Agent needs to have an entry point that can be called to run the
Agent. Before the introduction of this plugin system this was typically handled
within the ``__main__`` block.

Entry Point
-----------
After you have created the plugin file, you need to add the an entry point to
``setup.py``. This looks like (assuming the plugin file is called ``plugin.py``
and lives at the top level of the package):

.. code-block:: python

       entry_points={
           'ocs.plugins': [
               '<plugin name> = <package name>.plugin',
               ],
       },

Plugin name should just match the package name, however the group name must
always be ``ocs.plugins`` in order for OCS to recognize the plugin. For
example, in OCS this would be:

.. code-block:: python

       entry_points={
           'ocs.plugins': [
               'ocs = ocs.plugin',
               ],
       },

Testing
-------

You should now be able to start the new Agents through ``ocs-agent-cli``.
However, if you'd like to search for the plugin more directly you can do so by
running:

.. code-block:: python

    import sys
    if sys.version_info < (3, 10):
        from importlib_metadata import entry_points
    else:
        from importlib.metadata import entry_points
    
    discovered_plugins = entry_points(group='ocs.plugins')
    print(discovered_plugins)
    # [EntryPoint(name='ocs', value='ocs.plugin', group='ocs.plugins')]

===================
Contributing to OCS
===================

Branches
--------

Following release v0.10.1, ocs now has a single ``main`` branch, which replaces
the old ``master`` and ``develop`` branch model, described below. ``main``
functions like ``develop`` used to, and is the new default branch. Feature
branches should be based off of the latest ``main``, and pull requests should
be made into ``main``.

Users that want a "stable" installation of ocs should install from PyPI and/or
use tagged Docker images corresponding to the targeted release, i.e. v0.10.1.
Installing from source (i.e. from the ``main`` branch) comes with the usual
caveats of potential instability.

Old Branching Model
```````````````````

    **Note:** This branching model is no longer used, but the description is
    left here while we transition to the new one.

There are two long-lived branches in OCS, ``master`` and ``develop``.
``master`` should be considered stable, and will only move forward on official
releases. ``develop`` may be unstable, and is where all development should take
place.

What this means for you, the contributor, is that you should base your feature
branches off of the latest ``develop`` branch, and pull request them into
``develop``. Detailed steps below.

Pull Requests
-------------

If you are an SO collaborator you may have push access, in which case you can
push your feature branch, then open a pull request, selecting the ``main``
branch as the base branch.

If you are not an SO collaborator, or otherwise do not have push access, we
still welcome your pull request! You will have to fork the repository and
submit a PR from there. See the `GitHub documentation
<https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork>`_
for details on how to do so.

Releases
--------

    **Note:** Releases will be issued by core maintainers of OCS.

If you are trying to issue a release of OCS you should follow these steps:

1. Test the release properly builds and publishes with a pre-release. You can
   do so by pushing a tag matching ``v0.*.*a*``, ``v0.*.*b*``, or
   ``v0.*.*rc*``.
2. If no new commits are made following a pre-release, remove the pre-release
   tag. Multiple tags may prevent the official release from publishing properly.
3. Use the GitHub releases interface to draft a new release, creating a new tag
   targeting the ``main`` branch.
4. Write the release notes. Make use of the "Generate release notes" feature.
   It is helpful to organize these into sections as done in past releases. Be
   sure to highlight any breaking changes and include instructions for any
   actions users must take when updating.

Development Guide
-----------------

Contributors should follow the recommendations made in the `SO Developer Guide`_.

.. _SO Developer Guide: https://simons1.princeton.edu/docs/so_dev_guide/

pre-commit
``````````
As a way to enforce development guide recommendations we have configured
`pre-commit`_.  While not required, it is highly recommended you use this tool
when contributing to ocs. It will save both you and the reviewers time when
submitting pull requests.

You should set this up before making and committing your changes. To do so make
sure the ``pre-commit`` package is installed::

    $ pip install pre-commit

Then run::

    $ pre-commit install

This will install the configured git hooks and any dependencies. Now, whenever
you commit the hooks will run. If there are issues you will see them in the
output. This may automatically make changes to your staged files.  These
changes will be unstaged and need to be reviewed (typically with a ``git
diff``), restaged, and recommitted. For example, if you have trailing
whitespace on a line, pre-commit will prevent the commit and remove the
whitespace. You will then stage the new changes with another ``git add <file>``
and then re-run the commit. Here is the expected git output for this example:

.. code-block::

    $ vim demo.py
    $ git status
    On branch koopman/test-pre-commit
    Changes not staged for commit:
      (use "git add <file>..." to update what will be committed)
      (use "git restore <file>..." to discard changes in working directory)
        modified:   demo.py

    no changes added to commit (use "git add" and/or "git commit -a")
    $ git add demo.py
    $ git commit
    Check python ast.........................................................Passed
    Fix End of Files.........................................................Passed
    Trim Trailing Whitespace.................................................Failed
    - hook id: trailing-whitespace
    - exit code: 1
    - files were modified by this hook

    Fixing demo/demo.py

    $ git status
    On branch koopman/test-pre-commit
    Changes to be committed:
      (use "git restore --staged <file>..." to unstage)
        modified:   demo.py

    Changes not staged for commit:
      (use "git add <file>..." to update what will be committed)
      (use "git restore <file>..." to discard changes in working directory)
        modified:   demo.py
    $ git add -u
    $ git commit

.. _pre-commit: https://pre-commit.com/

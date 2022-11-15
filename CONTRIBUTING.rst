===================
Contributing to OCS
===================

Branches
--------

There are two long-lived branches in OCS, ``master`` and ``develop``.
``master`` should be considered stable, and will only move forward on official
releases. ``develop`` may be unstable, and is where all development should take
place.

What this means for you, the contributor, is that you should base your feature
branches off of the latest ``develop`` branch, and pull request them into
``develop``. Detailed steps below.

Pull Requests
-------------

When opening a pull request, you should push your feature branch, and select
the ``develop`` branch as the base branch, the branch you want to merge your
feature branch into.

Releases
--------

    **Note:** Releases will be issued by core maintainers of OCS.

If you are trying to issue a release of OCS you should follow these steps:

1. Open a Pull Request, comparing ``develop`` to the ``master`` base branch.
   Describe the features added for this release.
2. Make a merge commit when you merge this PR.

   * This merge commit will be what is tagged for the release.
   * ``develop`` is now one commit behind ``master`` (the merge commit)

3. Pull the latest ``master`` and ``develop`` branches to your work station.
4. Checkout ``develop``, then run ``git merge --ff-only master``, catching ``develop`` up to ``master``.
5. ``push origin develop`` to update the remote ``develop`` branch.

The ``develop`` and ``master`` branches are now aligned, and ``master`` is
ready to be released. You can use the GitHub release interface to create a new
release, copying the change log you wrote in the PR and otherwise describing the
release.

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

You should set this up before making and commiting your changes. To do so make
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

**Note:** This is a new tool to this repo, and the flake8 output might still be
somewhat strict. If there are warnings that you think should be ignored, please
bring this up for discussion in a new issue.

.. _pre-commit: https://pre-commit.com/

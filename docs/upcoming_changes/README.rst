:orphan:

Changelog
=========

This directory contains "news fragments" which are short files that contain a
small **ReST**-formatted text that will be added to the next what's new page.

Make sure to use full sentences with correct case and punctuation, and please
try to use Sphinx intersphinx using backticks. The fragment should have a
header line and an underline using ``------``

Each file should be named like ``<PULL REQUEST>.<TYPE>.rst``, where
``<PULL REQUEST>`` is a pull request number, and ``<TYPE>`` is one of:

* ``deprecation``: Changes existing code to emit a DeprecationWarning.
* ``new_feature``: New user facing features.
* ``improvement``: Bugfixes and Enhancements
* ``change``: Other changes
* ``highlight``: Adds a highlight bullet point to use as a possibly highlight
  of the release. For example, OpenGL renderer.
* ``docs``: Addition of Documentation.

It is possible to add two files with different categories (and text) if both
are relevant. For example a change may improve performance but have some
compatibility concerns.

Most categories should be formatted as paragraphs with a heading.
So for example: ``123.new_feature.rst`` would have the content::

    ``my_new_feature`` option for `my_favorite_function`
    ----------------------------------------------------
    The ``my_new_feature`` option is now available for `my_favorite_function`.
    To use it, write ``manim.my_favorite_function(..., my_new_feature=True)``.

``highlight`` is usually formatted as bulled points making the fragment
``* This is a highlight``.

Note the use of single-backticks to get an internal link (assuming
``my_favorite_function`` is exported from the ``manim`` namespace),
and double-backticks for code.

If you are unsure what pull request type to use, don't hesitate to ask in your
PR.

You can install ``towncrier`` and run ``towncrier --draft --version 1.18``
if you want to get a preview of how your change will look in the final release
notes.

.. note::

    This README was adapted from the pytest changelog readme under the terms of
    the MIT licence.

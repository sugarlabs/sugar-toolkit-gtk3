Sugar Toolkit GTK3
==================

Sugar Toolkit GTK3, or `sugar3`, is a toolkit for writing Sugar
activities in Python:

* write a `setup.py` which calls :class:`~sugar3.activity.bundlebuilder`,
* write an `activity/activity.info` file with metadata, see :class:`~sugar3.bundle`,
* write a class derived from :class:`~sugar3.activity.activity.Activity`,
* use the :class:`~sugar3.graphics` module classes to build a user interface.

Optional modules include:

* use the :class:`~sugar3.profile` module to fetch user profile information,
* use the :class:`~sugar3.presence` module classes to implement sharing,
* use the :class:`~sugar3.logger` module for debug logging,
* use the :class:`~sugar3.network` module for downloading data,
* use the :class:`~sugar3.speech` module for speech synthesis.

Indices and tables
==================

* :ref:`Functions and classes <genindex>`
* :ref:`Modules <modindex>`
* :ref:`search`

Table of Contents
=================

.. toctree::
   :maxdepth: 5

   sugar3

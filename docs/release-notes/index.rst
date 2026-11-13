.. meta::
   :description: Release notes for all versions of Chrony charms, including release policy and schedule.

.. _release_notes_index:

Release notes
=============

Release notes for the ``latest`` track of Chrony charms, summarizing new features,
bug fixes and backwards-incompatible changes in each revision.

For upgrading the charm, see :ref:`How to upgrade <how_to_upgrade>`.
For instructions on a specific release, see the corresponding release notes.

Release policy and schedule
---------------------------

For any given track, we use the ``edge`` and ``stable`` risk levels.
The release schedule for each of the risk levels is as follows:

1. Changes pushed to the ``chrony-operators`` repository will be released to ``edge``.
2. On the first day of every month, the current revision on ``edge`` will be promoted to ``stable``.
   This process requires an approval from the maintainers and happens automatically once the
   approval is given.

In special cases where an urgent fix is needed on ``stable``, changes can be pushed directly to
that risk level without going through the regular process.

Release notes are published for the ``chrony`` and ``chrony-client`` charms with every
revision of the ``latest/stable`` track.

Releases
--------

.. TODO: Add a list of releases here, with links to the individual release notes.
         Use a toctree directive

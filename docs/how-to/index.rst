.. meta::
   :description: How-to guides for operating the Chrony charms, including basic operations, upgrades, and development.

.. _how_to_index:

How-to guides
=============

Manage the full operations lifecycle of Chrony charms, from initial deployment
through production maintenance.
Each guide assumes that you've already deployed the charm with Juju.

.. vale Canonical.013-Spell-out-numbers-below-10 = NO
.. vale Canonical.500-Repeated-words = NO

Basic operations
----------------

Once you've finished setting up the charm, you can perform a number
of actions with your deployment. These guides provide instructions on
basic operations you can complete with the charm.

.. toctree::
    :maxdepth: 1

    Integrate with COS <integrate-with-cos>
    Configure time sources <setup-time-sources>
    Use NTS <enable-nts>

Update the charm
----------------

Upgrade the charms when new revisions are available to ensure that the
Chrony charms stay current and benefit from new features and capabilities.

.. toctree::
    :maxdepth: 1

    Upgrade <upgrade>

Development
-----------

These guides can help you with troubleshooting and contributing to the project.

.. toctree::
    :maxdepth: 1

    Contribute <contribute>

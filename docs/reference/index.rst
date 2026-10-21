.. meta::
   :description: Technical reference documentation for Chrony charms, including actions, configurations, and architecture.

.. _reference_index:

Reference
=========

Technical specifications and architectural details for Chrony charms serve
as authoritative look-up material when configuring, extending, or integrating
the charm.

Charm usage
-----------

Operators control charm behavior through configuration options and Juju
actions. Learn more about the available operation in configuration and relations.

.. vale Canonical.013-Spell-out-numbers-below-10 = NO
.. vale Canonical.500-Repeated-words = NO
.. vale Canonical.004-Canonical-product-names = NO

.. toctree::
    :hidden:
    :maxdepth: 1

    Configurations <configurations>
    Integrations <integrations>
    Metrics <metrics>
    Use NTS
.. vale Canonical.004-Canonical-product-names = YES

Architecture and deployments
----------------------------

Understanding the overall charm architecture include the components of the
charm and the design of the charm code.

.. toctree::
    :hidden:
    :maxdepth: 1

    Chrony charm architecture <operator-architecture>
    Chrony client charm architecture <high-level-deployment>

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=duplicate-code,missing-function-docstring

"""Charm unit tests."""

import ops.testing


def test_config_time_sources(harness: ops.testing.Harness):
    """
    arrange: initialize harness and simulate leader settings to arrange initial conditions.
    act: update configuration and set the time source.
    assert: the status changes appropriately and installation and restart methods are called.
    """
    harness.set_leader()
    harness.begin_with_initial_hooks()
    harness.charm.chrony.install.assert_called()

    harness.update_config({"sources": "ntp://example.com"})
    harness.charm.chrony.restart.assert_called()
    assert "pool example.com" in harness.charm.chrony.read_config()


def test_reconfig_time_sources(harness: ops.testing.Harness):
    """
    arrange: initialize harness and apply initial time source configuration to
        arrange test environment.
    act: change the time source configuration and assess the change impact.
    assert: verify that the configuration is updated, the old source is removed, the new source is
        added, and the restart method is invoked twice.
    """
    harness.begin_with_initial_hooks()
    harness.update_config({"sources": "ntp://example.com"})
    assert "pool example.com" in harness.charm.chrony.read_config()
    assert harness.charm.chrony.restart.call_count == 1

    harness.update_config({"sources": "ntp://example.net"})
    assert "pool example.com" not in harness.charm.chrony.read_config()
    assert "pool example.net" in harness.charm.chrony.read_config()
    assert harness.charm.chrony.restart.call_count == 2


def test_same_time_sources(harness: ops.testing.Harness):
    """
    arrange: arrange the testing environment with a time source configuration
    act: update the configuration with the same time source.
    assert: the time source remains unchanged and the restart method is not invoked again.
    """
    harness.begin_with_initial_hooks()
    harness.update_config({"sources": "ntp://example.com"})
    assert harness.charm.chrony.restart.call_count == 1

    harness.update_config({"sources": "ntp://example.com,"})
    assert harness.charm.chrony.restart.call_count == 1

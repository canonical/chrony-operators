#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import jubilant
import pytest


def test_time_sources(juju, chrony_client_app, chrony_app):
    """
    arrange: deploy the chrony-client and chrony charm.
    act: use the chrony charm as the time source for the chrony-client charm.
    assert: check if the chrony-client charm is using the time source.
    """
    server_ip = chrony_app.get_unit_ip()
    sources = f"ntp://{server_ip}?iburst=true"
    juju.config(chrony_client_app.name, {"sources": sources})
    juju.wait(
        lambda *args, **kwargs: jubilant.all_active(*args, **kwargs)
        and jubilant.all_agents_idle(*args, **kwargs)
    )

    assert server_ip in chrony_client_app.ssh("chronyc -N -n -c sources")


def test_chrony_exporter(chrony_client_app):
    """
    arrange: deploy the chrony-client charm.
    act: request chrony_exporter metrics endpoint.
    assert: confirm that metrics are scraped.
    """
    stdout = chrony_client_app.ssh("curl -m 10 localhost:9123/metrics")
    assert "chrony_sources_reachability_success" in stdout


def test_charm_conflict(juju, another_chrony_client_app):
    """
    arrange: deploy the chrony-client charm.
    act: deploy another chrony-client charm on the principle charm.
    assert: confirm that the second charm is in block state.
    """
    units = juju.status().get_units(another_chrony_client_app.name)
    status = units[another_chrony_client_app.get_leader_unit()].workload_status
    assert status.current == "blocked"
    assert "conflict" in status.message


def test_charm_uninstall_cleanup(juju, chrony_client_app, principle_app):
    """
    arrange: deploy the chrony-client charm.
    act: remove the chrony-client charm.
    assert: confirm that the chrony-charm related configuration and packages are removed
    """
    juju.remove_application(chrony_client_app.name)
    juju.wait(jubilant.all_active, timeout=20 * 60)

    with pytest.raises(jubilant.CLIError):
        principle_app.ssh("which chrony_exporter")

    assert "charm" not in principle_app.ssh("cat /etc/chrony/chrony.conf")

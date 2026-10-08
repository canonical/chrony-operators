# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for upgrading the chrony charm from Charmhub."""

import jubilant
from opcli.pytest_plugin import CharmPathList

from tests.integration.utils import ntp_request


def _active_and_idle(status: jubilant.Status) -> bool:
    """Return True when all applications are active and all agents are idle."""
    return jubilant.all_active(status) and jubilant.all_agents_idle(status)


def test_upgrade(juju: jubilant.Juju, charm_paths: dict[str, CharmPathList]):
    """
    arrange: deploy the chrony charm at the Charmhub revision that installs the
        exporter from the ppa:canonical-is-devops/chrony-charm PPA.
    act: refresh the application to the locally built charm, which bundles the
        exporter and removes the legacy PPA on install.
    assert: the legacy PPA sources file is removed after the upgrade, the
        bundled exporter still serves metrics, and the NTP server still responds.
    """
    juju.wait_timeout = 20 * 60
    juju.deploy(
        "chrony",
        app="chrony",
        channel="latest/edge",
        revision=117,
        base="ubuntu@24.04",
        config={"sources": "ntp://ntp.ubuntu.com"},
        constraints={"virt-type": "virtual-machine"},
    )
    juju.wait(_active_and_idle)

    # Sanity check: the legacy revision configures the PPA.
    sources_before = juju.ssh("chrony/0", "ls /etc/apt/sources.list.d/")
    assert "chrony-charm" in sources_before

    juju.refresh("chrony", path=charm_paths["chrony"].path)
    # The refresh returns while the application is still active from before the
    # upgrade, so wait for the upgrade hooks (which run _do_install and remove
    # the legacy PPA) to start before waiting for the application to settle
    # again, otherwise the assertions below observe the pre-upgrade state.
    juju.wait(lambda status: not jubilant.all_agents_idle(status))
    juju.wait(_active_and_idle)

    # The legacy PPA sources file must be removed after the upgrade.
    sources_after = juju.ssh("chrony/0", "ls /etc/apt/sources.list.d/")
    assert "chrony-charm" not in sources_after

    # The bundled exporter must still serve metrics.
    metrics = juju.ssh("chrony/0", "curl -m 10 localhost:9123/metrics")
    assert "chrony_serverstats_ntp_packets_received_total" in metrics

    # The NTP server must still respond after the upgrade.
    unit_ip = juju.status().get_units("chrony")["chrony/0"].public_address
    assert ntp_request(unit_ip)

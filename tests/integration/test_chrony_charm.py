# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging
import ssl
from collections.abc import Callable

import jubilant
import pytest
from opcli.pytest_plugin import CharmPathList

from tests.integration.utils import (
    gen_tls_certificate,
    get_sans,
    get_tls_certificates,
    ntp_request,
)

JUJU_WAIT_TIMEOUT = 20 * 60  # 20 minutes
CHRONY_APP = "chrony"
SELF_SIGNED_CERTIFICATES_APP = "self-signed-certificates"
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", name="chrony_app")
def chrony_app_fixture(juju: jubilant.Juju, charm_paths: dict[str, CharmPathList]) -> str:
    """Deploy the chrony charm and return its application name."""
    juju.wait_timeout = JUJU_WAIT_TIMEOUT
    juju.deploy(
        charm_paths[CHRONY_APP].path,
        app=CHRONY_APP,
        constraints={"virt-type": "virtual-machine"},
    )
    juju.wait(jubilant.all_agents_idle, timeout=JUJU_WAIT_TIMEOUT)
    return CHRONY_APP


@pytest.fixture(scope="module", name="self_signed_certificates_app")
def self_signed_certificates_app_fixture(juju: jubilant.Juju) -> str:
    """Deploy the self-signed-certificates charm and return its application name."""
    juju.deploy("self-signed-certificates", app=SELF_SIGNED_CERTIFICATES_APP)
    juju.wait(jubilant.all_agents_idle, timeout=JUJU_WAIT_TIMEOUT)
    return SELF_SIGNED_CERTIFICATES_APP


@pytest.fixture(name="get_unit_ips")
def get_unit_ips_fixture(juju: jubilant.Juju) -> Callable[..., list[str]]:
    """A function to get unit ips of a charm application."""

    def _get_unit_ips(name: str = CHRONY_APP) -> list[str]:
        units = juju.status().get_units(name)
        return [
            units[key].public_address for key in sorted(units, key=lambda n: int(n.split("/")[-1]))
        ]

    return _get_unit_ips


def _active_and_idle(status: jubilant.Status) -> bool:
    """Return True when all applications are active and all agents are idle."""
    return jubilant.all_active(status) and jubilant.all_agents_idle(status)


def test_build_and_deploy(juju: jubilant.Juju, chrony_app: str):
    """
    arrange: set up the chrony charm with a specific NTP source configuration.
    act: deploy the chrony charm and wait for it to reach the 'active' state.
    assert: ensure the application transitions to 'active' status after deployment.
    """
    juju.config(chrony_app, {"sources": "ntp://ntp.ubuntu.com"})
    juju.wait(_active_and_idle)


@pytest.mark.usefixtures("chrony_app")
def test_ntp_server(get_unit_ips: Callable[..., list[str]]):
    """
    arrange: set up the chrony charm with a specific NTP source configuration.
    act: send a simple NTPv4 request to each unit.
    assert: ensure each unit responds correctly to the NTP request.
    """
    unit_ips = get_unit_ips()
    for unit_ip in unit_ips:
        assert ntp_request(unit_ip)


def test_nts_certificates_integration(
    juju: jubilant.Juju,
    chrony_app: str,
    self_signed_certificates_app: str,
    get_unit_ips: Callable[..., list[str]],
):
    """
    arrange: relate with self-signed-certificate application.
    act: update chrony charm config to use different server names.
    assert: confirm that the SANs in the retrieved certificates match configured server name.
    """
    task = juju.run(f"{self_signed_certificates_app}/0", "get-ca-certificate")
    ca_cert = task.results["ca-certificate"]

    juju.config(chrony_app, {"server-name": "example.com", "sources": "ntp://ntp.ubuntu.com"})
    juju.integrate(chrony_app, self_signed_certificates_app)
    juju.wait(_active_and_idle, delay=2, successes=30)
    for unit_ip in get_unit_ips():
        cert = get_tls_certificates(unit_ip, cadata=ca_cert, server_name="example.com")
        assert sorted(get_sans(cert)) == sorted(["example.com", "*.example.com"])

    juju.config(chrony_app, {"server-name": "example.net"})
    juju.wait(_active_and_idle, delay=2, successes=30)
    for unit_ip in get_unit_ips():
        cert = get_tls_certificates(unit_ip, cadata=ca_cert, server_name="example.net")
        assert sorted(get_sans(cert)) == sorted(["example.net", "*.example.net"])
        with pytest.raises(ssl.SSLCertVerificationError):
            get_tls_certificates(unit_ip, cadata=ca_cert, server_name="example.com")


def test_nts_certificates_configuration(
    juju: jubilant.Juju, chrony_app: str, get_unit_ips: Callable[..., list[str]]
):
    """
    arrange: deploy the chrony charm.
    act: update chrony charm config to use a user supplied TLS certificate.
    assert: confirm that the SANs in the retrieved certificates match configured server name.
    """
    cert = gen_tls_certificate("config.test.net")
    secret_uri = juju.add_secret("test-cert", {"cert": cert.cert_pem, "key": cert.key_pem})
    juju.grant_secret("test-cert", chrony_app)
    juju.config(
        chrony_app, {"nts-certificates": str(secret_uri), "sources": "ntp://ntp.ubuntu.com"}
    )
    juju.wait(_active_and_idle, delay=2, successes=30)
    for unit_ip in get_unit_ips():
        remote_cert = get_tls_certificates(
            unit_ip, cadata=cert.cert_pem, server_name=cert.server_name
        )
        assert get_sans(remote_cert) == [cert.server_name]

    cert = gen_tls_certificate("config.test.org")
    juju.update_secret("test-cert", {"cert": cert.cert_pem, "key": cert.key_pem})
    juju.wait(_active_and_idle, delay=2, successes=30)
    for unit_ip in get_unit_ips():
        remote_cert = get_tls_certificates(
            unit_ip, cadata=cert.cert_pem, server_name=cert.server_name
        )
        assert get_sans(remote_cert) == [cert.server_name]


def test_chrony_exporter(juju: jubilant.Juju, chrony_app: str):
    """
    arrange: deploy the chrony charm.
    act: request chrony_exporter metrics endpoint.
    assert: confirm that metrics are scraped.
    """
    for unit in juju.status().get_units(chrony_app):
        stdout = juju.ssh(unit, "curl -m 10 localhost:9123/metrics")
        assert "chrony_serverstats_ntp_packets_received_total" in stdout

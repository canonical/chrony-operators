# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=duplicate-code,missing-function-docstring

"""Charm unit tests."""

import pathlib
import textwrap

import yaml
from ops import testing

import chrony_charm as charm
from chrony import TlsKeyPair
from chrony_charm import ChronyConfig

_CHARMCRAFT_META = yaml.safe_load(
    (pathlib.Path(__file__).resolve().parents[2] / "chrony-charmcraft.yaml").read_text()
)


def _context() -> testing.Context:
    """Build a scenario Context with the chrony charm metadata."""
    return testing.Context(charm.ChronyCharm, meta=_CHARMCRAFT_META)


def test_render_chrony_config(mock_chrony):
    """
    arrange: initialize Chrony object and parse time source URLs.
    act: generate a new configuration from parsed URLs.
    assert: verify that the rendered configuration matches the expected output.
    """
    sources = [
        mock_chrony.parse_source_url(s) for s in ["ntp://example.com", "nts://nts.example.com"]
    ]
    assert ChronyConfig(chrony=mock_chrony, sources=sources).render() == textwrap.dedent(
        """\
        pool example.com
        pool nts.example.com nts

        bindcmdaddress 127.0.0.1
        driftfile /var/lib/chrony/chrony.drift
        ntsdumpdir /var/lib/chrony
        logdir /var/log/chrony
        maxupdateskew 100.0
        rtcsync
        makestep 1 3
        leapsectz right/UTC
        allow 0.0.0.0/0
        allow ::/0
        """
    )


def test_render_chrony_config_with_certs(mock_chrony):
    """
    arrange: initialize Chrony object and parse time source URLs.
    act: generate a new configuration from parsed URLs and provided TLS credentials.
    assert: verify that the rendered configuration matches the expected output.
    """
    sources = [mock_chrony.parse_source_url("ntp://example.com")]
    certs = [
        TlsKeyPair(certificate="1-cert", key="1-key"),
        TlsKeyPair(certificate="2-cert", key="2-key"),
    ]
    certs_dir = mock_chrony.CERTS_DIR
    assert ChronyConfig(
        chrony=mock_chrony, sources=sources, tls_key_pairs=certs
    ).render() == textwrap.dedent(
        f"""\
        pool example.com

        ntsservercert {certs_dir}/0000.crt
        ntsserverkey {certs_dir}/0000.key
        ntsservercert {certs_dir}/0001.crt
        ntsserverkey {certs_dir}/0001.key

        bindcmdaddress 127.0.0.1
        driftfile /var/lib/chrony/chrony.drift
        ntsdumpdir /var/lib/chrony
        logdir /var/log/chrony
        maxupdateskew 100.0
        rtcsync
        makestep 1 3
        leapsectz right/UTC
        allow 0.0.0.0/0
        allow ::/0
        """
    )


def test_config_time_sources(mock_chrony, mock_tls_keychain):
    """
    arrange: run the install event to arrange initial conditions.
    act: update configuration and set the time source.
    assert: the installation and restart methods are called and the config is rendered.
    """
    ctx = _context()
    state = testing.State(leader=True, config={"sources": "ntp://example.com"})

    ctx.run(ctx.on.install(), state)
    assert mock_chrony.install.called

    ctx.run(ctx.on.config_changed(), state)
    assert mock_chrony.restart.called
    assert "pool example.com" in mock_chrony.read_config()


def test_reconfig_time_sources(mock_chrony, mock_tls_keychain):
    """
    arrange: apply initial time source configuration.
    act: change the time source configuration and assess the change impact.
    assert: verify that the configuration is updated, the old source is removed, the new source is
        added, and the restart method is invoked twice.
    """
    ctx = _context()

    ctx.run(ctx.on.config_changed(), testing.State(config={"sources": "ntp://example.com"}))
    assert "pool example.com" in mock_chrony.read_config()
    assert mock_chrony.restart.call_count == 1

    ctx.run(ctx.on.config_changed(), testing.State(config={"sources": "ntp://example.net"}))
    assert "pool example.com" not in mock_chrony.read_config()
    assert "pool example.net" in mock_chrony.read_config()
    assert mock_chrony.restart.call_count == 2


def test_same_time_sources(mock_chrony, mock_tls_keychain):
    """
    arrange: arrange the testing environment with a time source configuration.
    act: update the configuration with the same time source.
    assert: the time source remains unchanged and the restart method is not invoked again.
    """
    ctx = _context()

    ctx.run(ctx.on.config_changed(), testing.State(config={"sources": "ntp://example.com"}))
    assert mock_chrony.restart.call_count == 1

    ctx.run(ctx.on.config_changed(), testing.State(config={"sources": "ntp://example.com,"}))
    assert mock_chrony.restart.call_count == 1

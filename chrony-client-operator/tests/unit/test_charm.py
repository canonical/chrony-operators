# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Learn more about testing at: https://ops.readthedocs.io/en/latest/explanation/testing.html

# pylint: disable=duplicate-code,missing-function-docstring,protected-access

"""Unit tests."""

import textwrap

import pytest
from ops import testing

import charm
import chrony


@pytest.mark.parametrize(
    "sources, valid, source_config",
    [
        pytest.param(
            "ntp://example.com",
            True,
            "pool example.com",
            id="ntp server",
        ),
        pytest.param(
            "ntp://example.com:1234",
            True,
            "pool example.com port 1234",
            id="ntp server with port",
        ),
        pytest.param(
            "ntp://example.com?iburst=true",
            True,
            "pool example.com iburst",
            id="ntp server with iburst option",
        ),
        pytest.param(
            "ntp://example.com:1234?iburst=true&minpoll=10&polltarget=50",
            True,
            "pool example.com port 1234 iburst minpoll 10 polltarget 50",
            id="ntp server with multiple option",
        ),
        pytest.param(
            "nts://example.com?require=true&offset=-0.1",
            True,
            "pool example.com nts offset -0.1 require",
            id="nts server",
        ),
        pytest.param(
            textwrap.dedent(
                """\
                ntp://ntp.ubuntu.com?iburst=true&maxsources=4,
                ntp://0.ubuntu.pool.ntp.org?iburst=true&maxsources=1,
                ntp://1.ubuntu.pool.ntp.org?iburst=true&maxsources=1,
                ntp://2.ubuntu.pool.ntp.org?iburst=true&maxsources=2
                """
            ),
            True,
            textwrap.dedent(
                """\
                pool ntp.ubuntu.com iburst maxsources 4
                pool 0.ubuntu.pool.ntp.org iburst maxsources 1
                pool 1.ubuntu.pool.ntp.org iburst maxsources 1
                pool 2.ubuntu.pool.ntp.org iburst maxsources 2
                """
            ),
            id="multiple ntp server",
        ),
        pytest.param(
            "example.com",
            False,
            "",
            id="invalid ntp server",
        ),
        pytest.param(
            "",
            False,
            "",
            id="no sources",
        ),
        pytest.param(
            "example.com",
            False,
            "",
            id="invalid sources: no protocol",
        ),
        pytest.param(
            "example.com:99999",
            False,
            "",
            id="invalid sources: invalid port",
        ),
        pytest.param(
            "https://example.com",
            False,
            "",
            id="invalid sources: unknown protocol",
        ),
        pytest.param(
            "ntp://example.com?foobar=true",
            False,
            "",
            id="invalid sources: unknown param",
        ),
    ],
)
def test_chrony_config(sources: str, valid: bool, source_config: str, mock_chrony: chrony.Chrony):
    """
    arrange: none.
    act: trigger the 'config-changed' event with different sources charm configuration.
    assert: check if configuration file content matches the charm configuration.
    """
    mock_chrony.write_config("default")

    ctx = testing.Context(charm.ChronyClientCharm)
    state_in = testing.State(
        config={"sources": sources},
        relations=[testing.SubordinateRelation(endpoint="juju-info", id=1)],
    )

    state_out = ctx.run(ctx.on.config_changed(), state_in)

    assert charm.ChronyClientCharm._read_chrony_lock_file() == "chrony-client"

    if not valid:
        assert state_out.unit_status.name == testing.BlockedStatus.name
        assert mock_chrony.read_config() == "default"
        assert not mock_chrony.restart.called
        return

    assert state_out.unit_status == testing.ActiveStatus()
    expected_config = (
        charm.CHRONY_CHARM_CONFIG_HEADER
        + "\n\n"
        + source_config.strip()
        + "\n"
        + textwrap.dedent(
            """
            sourcedir /run/chrony-dhcp
            sourcedir /etc/chrony/sources.d
            keyfile /etc/chrony/chrony.keys
            driftfile /var/lib/chrony/chrony.drift
            ntsdumpdir /var/lib/chrony
            logdir /var/log/chrony
            maxupdateskew 100.0
            rtcsync
            makestep 1 3
            leapsectz right/UTC
            """
        )
    )
    assert mock_chrony.read_config() == expected_config
    mock_chrony.restart.assert_called_once()


def test_chrony_uninstall(mock_chrony: chrony.Chrony):
    """
    arrange: run the `config-changed` event
    act: trigger the 'remove' event.
    assert: check if configuration file content and packages are restored.
    """
    mock_chrony.write_config("default")

    ctx = testing.Context(charm.ChronyClientCharm)
    state_in = testing.State(
        config={"sources": "ntp://example.com"},
        relations=[testing.SubordinateRelation(endpoint="juju-info", id=1)],
    )
    ctx.run(ctx.on.config_changed(), state_in)

    ctx = testing.Context(charm.ChronyClientCharm)
    state_in = testing.State(
        config={"sources": "ntp://example.com"},
        relations=[testing.SubordinateRelation(endpoint="juju-info", id=1)],
    )
    ctx.run(ctx.on.remove(), state_in)

    assert charm.ChronyClientCharm._read_chrony_lock_file() is None
    assert mock_chrony.read_config() == "default"
    mock_chrony.uninstall.assert_called_once()

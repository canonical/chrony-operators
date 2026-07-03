# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=duplicate-code,missing-function-docstring

"""Chrony unit tests."""

import textwrap

import pytest

from src.chrony import Chrony, TlsKeyPair

TIME_SOURCE_URL_EXAMPLES = [
    ["ntp://example.com", "pool example.com"],
    ["ntp://example.com:1234", "pool example.com port 1234"],
    ["ntp://example.com?iburst=true", "pool example.com iburst"],
    ["ntp://example.com?iburst=True", "pool example.com iburst"],
    ["ntp://example.com?iburst=TRUE", "pool example.com iburst"],
    ["ntp://example.com?iburst=1", "pool example.com iburst"],
    ["ntp://example.com?iburst=false", "pool example.com"],
    ["ntp://example.com?iburst=False", "pool example.com"],
    ["ntp://example.com?iburst=FALSE", "pool example.com"],
    ["ntp://example.com?iburst=0", "pool example.com"],
    [
        "ntp://example.com:1234?iburst=true&minpoll=10&polltarget=50",
        "pool example.com port 1234 iburst minpoll 10 polltarget 50",
    ],
    ["nts://example.com?require=true&offset=-0.1", "pool example.com nts offset -0.1 require"],
    ["nts://example.com:4461?require=true", "pool example.com nts ntsport 4461 require"],
]


@pytest.mark.parametrize("url,directive", TIME_SOURCE_URL_EXAMPLES)
def test_parse_source_url(url: str, directive: str):
    """
    arrange: receive a list of URL and directory pairs for testing.
    act: parse the source URL to get a configuration directive.
    assert: confirm that the rendered directory matches the expected directive.
    """
    assert Chrony.parse_source_url(url).render() == directive


INVALID_TIME_SOURCE_URL_EXAMPLES = [
    pytest.param("https://example.com", id="invalid protocol"),
    pytest.param("ntp://", id="no host"),
    pytest.param("ntp://example.com?offset=test", id="incorrect option type"),
    pytest.param("ntp://example.com?foobar=123", id="unknown options"),
]


@pytest.mark.parametrize("url", INVALID_TIME_SOURCE_URL_EXAMPLES)
def test_parse_invalid_source_url(url: str):
    """
    arrange: provide a list of invalid URL examples for parsing.
    act: attempt to parse the source URL which should be invalid.
    assert: expect a ValueError to be raised due to invalid URL format.
    """
    with pytest.raises(ValueError):
        Chrony.parse_source_url(url)


def test_render_chrony_config():
    """
    arrange: initialize Chrony object and parse time source URLs.
    act: generate a new configuration from parsed URLs.
    assert: verify that the rendered configuration matches the expected output.
    """
    chrony = Chrony()
    sources = [chrony.parse_source_url(s) for s in ["ntp://example.com", "nts://nts.example.com"]]
    assert chrony.new_config(sources=sources).render() == textwrap.dedent(
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


def test_read_write_certs(harness):
    """
    arrange: initialize harness and Chrony object.
    act: write a sequence of TLS key pairs into the TLS keychain.
    assert: verify that the TLS keychain contents matches the expected input.
    """
    harness.begin()
    chrony = harness.charm.chrony
    assert not chrony.read_tls_key_pairs()

    transformation = [
        [TlsKeyPair(certificate="foobar-cert", key="foobar-key")],
        [TlsKeyPair(certificate="1-cert", key="1-key")],
        [
            TlsKeyPair(certificate="1-cert", key="1-key"),
            TlsKeyPair(certificate="2-cert", key="2-key"),
        ],
        [
            TlsKeyPair(certificate="0-cert", key="0-key"),
            TlsKeyPair(certificate="1-cert", key="1-key"),
        ],
        [
            TlsKeyPair(certificate="1-cert", key="1-key"),
        ],
        [
            TlsKeyPair(certificate="1-cert", key="1-key"),
            TlsKeyPair(certificate="2-cert", key="2-key"),
        ],
        [
            TlsKeyPair(certificate="cert", key="key"),
            TlsKeyPair(certificate="2-cert", key="2-key"),
        ],
        [
            TlsKeyPair(certificate="1-cert", key="1-key"),
        ],
        [],
    ]

    for certs in transformation:
        chrony.write_tls_key_pairs(certs)
        assert chrony.read_tls_key_pairs() == certs


def test_render_chrony_config_with_certs():
    """
    arrange: initialize Chrony object and parse time source URLs.
    act: generate a new configuration from parsed URLs and provided TLS credentials.
    assert: verify that the rendered configuration matches the expected output.
    """
    chrony = Chrony()
    sources = [chrony.parse_source_url("ntp://example.com")]
    certs = [
        TlsKeyPair(certificate="1-cert", key="1-key"),
        TlsKeyPair(certificate="2-cert", key="2-key"),
    ]
    assert chrony.new_config(sources=sources, tls_key_pairs=certs).render() == textwrap.dedent(
        """\
        pool example.com

        ntsservercert /etc/chrony/certs/0000.crt
        ntsserverkey /etc/chrony/certs/0000.key
        ntsservercert /etc/chrony/certs/0001.crt
        ntsserverkey /etc/chrony/certs/0001.key

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

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=duplicate-code,missing-function-docstring

"""Chrony unit tests."""

import pytest

from chrony import Chrony, TlsKeyPair

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


def test_read_write_certs(mock_chrony):
    """
    arrange: initialize Chrony object.
    act: write a sequence of TLS key pairs into the TLS keychain.
    assert: verify that the TLS keychain contents matches the expected input.
    """
    chrony = mock_chrony
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

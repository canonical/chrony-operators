# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=duplicate-code,missing-function-docstring

"""Chrony unit tests."""


def test_keychain_private_key(mock_tls_keychain):
    """
    arrange: mock filesystem operations in TlsKeychain.
    act: write a private key to the given TlsKeychain.
    assert: read the private key from the given TlsKeychain gives the same private key.
    """
    assert mock_tls_keychain.get_private_key() is None
    mock_tls_keychain.set_private_key("foobar")
    assert mock_tls_keychain.get_private_key() == "foobar"
    mock_tls_keychain.set_private_key("test")
    assert mock_tls_keychain.get_private_key() == "test"


def test_keychain_server_name(mock_tls_keychain):
    """
    arrange: mock filesystem operations in TlsKeychain.
    act: write the server name to the given TlsKeychain.
    assert: read the server name from the given TlsKeychain gives the same server name.
    """
    assert mock_tls_keychain.get_server_name() is None
    mock_tls_keychain.set_server_name("foobar")
    assert mock_tls_keychain.get_server_name() == "foobar"
    mock_tls_keychain.set_server_name("test")
    assert mock_tls_keychain.get_server_name() == "test"


def test_keychain_chain(mock_tls_keychain):
    """
    arrange: mock filesystem operations in TlsKeychain.
    act: write the certificate chain to the given TlsKeychain.
    assert: read the certificate chain from the given TlsKeychain gives the same certificate chain.
    """
    assert mock_tls_keychain.get_chain() is None
    mock_tls_keychain.set_chain("foobar")
    assert mock_tls_keychain.get_chain() == "foobar"
    mock_tls_keychain.set_chain("test")
    assert mock_tls_keychain.get_chain() == "test"

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Scenario test fixtures."""

import json

import cryptography.hazmat.primitives.serialization
import pytest
from charms.tls_certificates_interface.v3 import tls_certificates
from scenario import Secret

from tests.utils import TEST_CA_CERT, sign_csr


class Helper:
    """Scenario test helper."""

    def __init__(self, server_name: str, tls_keychain, chrony):
        """Initialize scenario test helper."""
        self.tls_keychain = tls_keychain
        self.chrony = chrony
        self.server_name = server_name
        self.ca_cert = (
            TEST_CA_CERT.public_bytes(cryptography.hazmat.primitives.serialization.Encoding.PEM)
            .decode("ascii")
            .strip()
        )
        self.csr = (
            tls_certificates.generate_csr(
                private_key=tls_keychain.get_private_key().encode(),
                subject="example.com",
                sans_dns=["example.com", "*.example.com"],
            )
            .decode("ascii")
            .strip()
        )
        self.cert = sign_csr(self.csr).strip()
        self.chain = [self.cert, self.ca_cert]

    def get_local_unit_data(self):
        """Get simulated local unit data for nts-certificates integration."""
        return {
            "certificate_signing_requests": json.dumps(
                [{"certificate_signing_request": self.csr, "ca": False}]
            )
        }

    def get_revoked_remote_app_data(self):
        """Get simulated remote app data for nts-certificates integration when provider revoked
        provided certificates.
        """
        data = self.get_remote_app_data()
        return {
            "certificates": json.dumps(
                [{"revoked": True, **cert} for cert in json.loads(data["certificates"])]
            )
        }

    def get_remote_app_data(self):
        """Get simulated remote app data for nts-certificates integration."""
        return {
            "certificates": json.dumps(
                [
                    {
                        "ca": self.ca_cert,
                        "chain": self.chain,
                        "certificate_signing_request": self.csr,
                        "certificate": self.cert,
                    }
                ]
            )
        }

    def get_tls_certificates_secret(self):
        """Get simulated tls certificates secret created by tls-certificates library."""
        return Secret(
            id="secret:foobar",
            label=f"{tls_certificates.LIBID}-{tls_certificates.get_sha256_hex(self.csr)}",
            tracked_content={"certificate": self.cert, "csr": self.csr},
            owner="unit",
        )

    def write_server_name_and_csr(self):
        """Write server name and csr to TLS keychain."""
        self.tls_keychain.set_server_name(self.server_name)
        self.tls_keychain.set_csr(self.csr)

    def write_chain(self):
        """Write certificate chain to TLS keychain."""
        self.tls_keychain.set_chain("\n\n".join(self.chain))


@pytest.fixture
def helper(mock_tls_keychain, mock_chrony):
    """Create scenario test helper and write the private key to TLS keychain."""
    mock_tls_keychain.set_private_key(tls_certificates.generate_private_key().decode("ascii"))
    return Helper(server_name="example.com", tls_keychain=mock_tls_keychain, chrony=mock_chrony)

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""

import json
import pathlib
from unittest.mock import patch

import cryptography.hazmat.primitives.serialization
import pytest
from charms.tls_certificates_interface.v3 import tls_certificates
from ops.testing import Secret

import chrony
import keychain
from tests.utils import TEST_CA_CERT, sign_csr


@pytest.fixture(name="patch_charm", autouse=True)
def patch_charm_fixture():
    """Patch necessary functions in the charm."""
    chrony_lock_file = None

    def _write_chrony_lock_file(content: str) -> None:
        nonlocal chrony_lock_file
        chrony_lock_file = content

    def _read_chrony_lock_file() -> None | str:
        return chrony_lock_file

    def _delete_chrony_lock_file():
        nonlocal chrony_lock_file
        chrony_lock_file = None

    with (
        patch(
            "chrony_client_charm.ChronyClientCharm._write_chrony_lock_file"
        ) as mock_write_chrony_lock_file,
        patch(
            "chrony_client_charm.ChronyClientCharm._read_chrony_lock_file"
        ) as mock_read_chrony_lock_file,
        patch(
            "chrony_client_charm.ChronyClientCharm._delete_chrony_lock_file"
        ) as mock_delete_chrony_lock_file,
    ):
        mock_write_chrony_lock_file.side_effect = _write_chrony_lock_file
        mock_read_chrony_lock_file.side_effect = _read_chrony_lock_file
        mock_delete_chrony_lock_file.side_effect = _delete_chrony_lock_file
        yield


@pytest.fixture(name="mock_chrony", autouse=True)
def mock_chrony_fixture(tmp_path_factory):  # noqa: C901 pylint: disable=too-many-locals
    """Create a Chrony object with necessary methods patched."""
    certs_dir = tmp_path_factory.mktemp("chrony_certs")
    installed = False

    def install():
        nonlocal installed
        installed = True

    def uninstall():
        nonlocal installed
        installed = False

    mock_config = ""

    def read_config():
        return mock_config

    def write_config(config: str):
        nonlocal mock_config
        mock_config = config

    certs: dict[str, str] = {}

    def _iter_certs_dir():
        for file in certs:
            yield pathlib.Path("/etc/chrony/certs") / file

    def _write_certs_file(path: pathlib.Path, content: str):
        certs[path.name] = content

    def _read_certs_file(path: pathlib.Path):
        return certs[path.name]

    def _unlink_certs_file(path: pathlib.Path) -> None:
        del certs[path.name]

    backup_config_content = None

    def backup_config():
        nonlocal backup_config_content
        backup_config_content = read_config()

    def restore_config():
        if backup_config_content is not None:
            write_config(backup_config_content)

    with (
        patch("chrony.Chrony.CERTS_DIR", certs_dir),
        patch("chrony.Chrony.install") as mock_install,
        patch("chrony.Chrony.uninstall") as mock_uninstall,
        patch("chrony.Chrony.remove_legacy_ppa_exporter"),
        patch("chrony.Chrony.restart"),
        patch("chrony.Chrony.write_config") as mock_write_config,
        patch("chrony.Chrony.read_config") as mock_read_config,
        patch("chrony.Chrony.backup_config") as mock_backup_config,
        patch("chrony.Chrony.restore_config") as mock_restore_config,
        patch("chrony.Chrony._make_certs_dir"),
        patch("chrony.Chrony._iter_certs_dir") as mock_iter_certs_dir,
        patch("chrony.Chrony._write_certs_file") as mock_write_certs_file,
        patch("chrony.Chrony._read_certs_file") as mock_read_certs_file,
        patch("chrony.Chrony._unlink_certs_file") as mock_unlink_certs_file,
    ):
        mock_install.side_effect = install
        mock_uninstall.side_effect = uninstall
        mock_read_config.side_effect = read_config
        mock_write_config.side_effect = write_config
        mock_backup_config.side_effect = backup_config
        mock_restore_config.side_effect = restore_config
        mock_iter_certs_dir.side_effect = _iter_certs_dir
        mock_write_certs_file.side_effect = _write_certs_file
        mock_read_certs_file.side_effect = _read_certs_file
        mock_unlink_certs_file.side_effect = _unlink_certs_file
        yield chrony.Chrony()


@pytest.fixture(name="mock_tls_keychain")
def mock_tls_keychain_fixture(tmp_path_factory):
    """Create a TlsKeychain object with necessary methods patched."""
    var_lib_chrony = tmp_path_factory.mktemp("var_lib_chrony")
    with patch.object(keychain.TlsKeychain, "STORAGE_DIR", var_lib_chrony / "tls-keychain"):
        yield keychain.TlsKeychain(namespace="nts-certificates")


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

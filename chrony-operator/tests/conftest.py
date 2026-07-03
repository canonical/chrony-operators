# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""

import pathlib
import typing
from unittest.mock import patch

import ops.testing
import pytest

import chrony
import keychain
from charm import ChronyCharm


@pytest.fixture(name="mock_chrony")
def mock_chrony_fixture():
    """Create a Chrony object with necessary methods patched."""
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

    with (
        patch("chrony.Chrony.install"),
        patch("chrony.Chrony.restart"),
        patch("chrony.Chrony.write_config") as mock_write_config,
        patch("chrony.Chrony.read_config") as mock_read_config,
        patch("chrony.Chrony._make_certs_dir"),
        patch("chrony.Chrony._iter_certs_dir") as mock_iter_certs_dir,
        patch("chrony.Chrony._write_certs_file") as mock_write_certs_file,
        patch("chrony.Chrony._read_certs_file") as mock_read_certs_file,
        patch("chrony.Chrony._unlink_certs_file") as mock_unlink_certs_file,
    ):
        mock_read_config.side_effect = read_config
        mock_write_config.side_effect = write_config
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


@pytest.fixture
def harness(  # pylint: disable=unused-argument
    mock_chrony, mock_tls_keychain
) -> typing.Generator[ops.testing.Harness, None, None]:
    """Create ops.testing.Harness object and patch necessary functions in code."""
    yield ops.testing.Harness(ChronyCharm)

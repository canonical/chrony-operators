# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""

import pathlib
from unittest.mock import patch

import pytest

import chrony


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
        patch("charm.ChronyClientCharm._write_chrony_lock_file") as mock_write_chrony_lock_file,
        patch("charm.ChronyClientCharm._read_chrony_lock_file") as mock_read_chrony_lock_file,
        patch("charm.ChronyClientCharm._delete_chrony_lock_file") as mock_delete_chrony_lock_file,
    ):
        mock_write_chrony_lock_file.side_effect = _write_chrony_lock_file
        mock_read_chrony_lock_file.side_effect = _read_chrony_lock_file
        mock_delete_chrony_lock_file.side_effect = _delete_chrony_lock_file
        yield


@pytest.fixture(name="mock_chrony", autouse=True)
def mock_chrony_fixture():  # noqa: C901 pylint: disable=too-many-locals
    """Create a Chrony object with necessary methods patched."""
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
        patch("chrony.Chrony.install") as mock_install,
        patch("chrony.Chrony.uninstall") as mock_uninstall,
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

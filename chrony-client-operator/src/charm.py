#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Learn more at: https://juju.is/docs/sdk

"""Chrony charm."""

import logging
import pathlib
import shutil
import textwrap
import typing

import ops
from charms.grafana_agent.v0.cos_agent import COSAgentProvider

from chrony import Chrony, TimeSource

logger = logging.getLogger(__name__)

CHRONY_CHARM_LOCK_FILE = pathlib.Path("/var/lib/chrony-charm/lock")
CHRONY_CHARM_CONFIG_HEADER = textwrap.dedent(
    """\
    # This is managed by chrony-client charm (https://charmhub.io/chrony-client).
    # Do not edit.\
    """
)


class ChronyClientCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.chrony = Chrony()
        self._grafana_agent = COSAgentProvider(
            self,
            metrics_endpoints=[
                {"path": "/metrics", "port": 9123},
            ],
            dashboard_dirs=["./src/grafana_dashboards"],
        )
        self.framework.observe(self.on.install, self._do_install_and_config)
        self.framework.observe(self.on.remove, self._on_remove)
        self.framework.observe(self.on.upgrade_charm, self._do_install_and_config)
        self.framework.observe(self.on.config_changed, self._do_install_and_config)

    def _do_install_and_config(self, _: ops.EventBase) -> None:
        """Install required packages and open NTP port."""
        if self._try_acquire_chrony_lock():
            if not self.chrony.is_installed():
                self.unit.status = ops.MaintenanceStatus("installing chrony")
                self.chrony.install()
            self._configure_chrony()
        else:
            self._set_lock_failure_status()

    def _on_remove(self, _: ops.EventBase) -> None:
        """Handle remove event."""
        if self._try_acquire_chrony_lock():
            self.chrony.uninstall()
            self.chrony.restore_config()
            self.chrony.restart()
            self._release_chrony_lock()

    def _configure_chrony(self) -> None:
        """Configure chrony."""
        try:
            sources = self._get_time_sources()
        except ValueError:
            self.unit.status = ops.BlockedStatus("invalid sources configuration")
            return
        if not sources:
            self.unit.status = ops.BlockedStatus("no time source configured")
            return
        if CHRONY_CHARM_CONFIG_HEADER not in self.chrony.read_config():
            self.chrony.backup_config()
        new_config = self.chrony.new_config(sources=sources, header=CHRONY_CHARM_CONFIG_HEADER)
        current_config = self.chrony.read_config()
        if new_config != current_config:
            logger.info("Chrony config changed, apply and restart chrony")
            self.chrony.write_config(new_config)
            self.chrony.restart()

        self.unit.status = ops.ActiveStatus()

    def _get_time_sources(self) -> list[TimeSource]:
        """Get time sources from charm configuration.

        Returns:
            Time source objects.
        """
        urls = typing.cast(str, self.config.get("sources"))
        return [
            self.chrony.parse_source_url(url.strip()) for url in urls.split(",") if url.strip()
        ]

    @staticmethod
    def _write_chrony_lock_file(content: str) -> None:
        """Write chrony charm lock file.

        Args:
            content: lock file content.
        """
        CHRONY_CHARM_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        CHRONY_CHARM_LOCK_FILE.write_text(content, encoding="utf-8")

    @staticmethod
    def _read_chrony_lock_file() -> typing.Optional[str]:
        """Read chrony charm lock file.

        Returns:
            None if lock file doesn't exist, otherwise lock file content.
        """
        if CHRONY_CHARM_LOCK_FILE.exists():
            return CHRONY_CHARM_LOCK_FILE.read_text(encoding="utf-8")
        return None

    @staticmethod
    def _delete_chrony_lock_file() -> None:
        """Delete chrony charm lock file."""
        shutil.rmtree(CHRONY_CHARM_LOCK_FILE.parent)

    def _try_acquire_chrony_lock(self) -> bool:
        """Try to acquire chrony lock.

        The chrony lock ensures that when multiple instances of the
        chrony charm are installed on the same machine, only one
        chrony charm application will execute.

        Returns:
            True if lock acquired, False otherwise.
        """
        lock_content = self.app.name
        lock_file = self._read_chrony_lock_file()
        if lock_file is None:
            self._write_chrony_lock_file(lock_content)
            return True
        return lock_file.strip() == lock_content

    def _release_chrony_lock(self) -> None:
        """Release chrony lock.

        Remove the chrony charm lock file.
        """
        if self._try_acquire_chrony_lock():
            self._delete_chrony_lock_file()
        else:
            raise RuntimeError("failed to delete the lock file: owned by another charm")

    def _set_lock_failure_status(self) -> None:
        """Set unit status to inform user to remove this charm application."""
        self.unit.status = ops.BlockedStatus(
            "conflict: multiple chrony charms detected, "
            f"remove this charm using `juju remove-application {self.app.name}`"
        )


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(ChronyClientCharm)

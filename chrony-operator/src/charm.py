#!/usr/bin/env python3

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

# Learn more at: https://juju.is/docs/sdk

"""Chrony charm."""

import logging
import typing

import ops
from charms.grafana_agent.v0.cos_agent import COSAgentProvider
from charms.tls_certificates_interface.v3 import tls_certificates

from chrony import Chrony, TimeSource, TlsKeyPair
from keychain import TlsKeychain

logger = logging.getLogger(__name__)


class ChronyCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.chrony = Chrony()
        self.certificates = tls_certificates.TLSCertificatesRequiresV3(self, "nts-certificates")
        self.tls_keychain = TlsKeychain(namespace="nts-certificates")
        self._grafana_agent = COSAgentProvider(
            self,
            metrics_endpoints=[
                {"path": "/metrics", "port": 9123},
            ],
            dashboard_dirs=["./src/grafana_dashboards"],
        )
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.secret_changed, self._on_secret_changed)
        self.framework.observe(
            self.on.nts_certificates_relation_created, self._on_certificates_relation_created
        )
        self.framework.observe(
            self.on.nts_certificates_relation_broken, self._on_certificates_relation_broken
        )
        self.framework.observe(
            self.certificates.on.certificate_available, self._on_certificate_available
        )
        self.framework.observe(
            self.certificates.on.certificate_expiring, self._on_certificate_expiring
        )
        self.framework.observe(
            self.certificates.on.certificate_invalidated, self._on_certificate_invalidated
        )
        self.framework.observe(self.on.collect_unit_status, self._on_collect_unit_status)

    def _on_collect_unit_status(self, _: ops.CollectStatusEvent) -> None:
        """Set unit status based on current charm status."""
        if not self._get_time_sources():
            self.unit.status = ops.BlockedStatus("no time source configured")
            return
        if not self._get_server_name() and self.model.get_relation("nts-certificates"):
            self.unit.status = ops.BlockedStatus(
                "server-name is required for nts-certificates integration"
            )
            return
        if self.certificates.get_certificate_signing_requests(unfulfilled_only=True):
            self.unit.status = ops.WaitingStatus("waiting for new certificate")
            return
        self.unit.status = ops.ActiveStatus()

    def _on_certificates_relation_created(self, _: ops.RelationCreatedEvent) -> None:
        """Handle the certificates relation-creation event."""
        self._do_renew_certificate()

    def _on_certificates_relation_broken(self, _: ops.RelationBrokenEvent) -> None:
        """Handle the certificates relation-broken event."""
        self.tls_keychain.clear()
        self._configure_chrony()

    def _on_certificate_expiring(self, _: ops.EventBase) -> None:
        """Handle the certificates expiring event."""
        self._do_renew_certificate()

    def _on_certificate_invalidated(self, _: ops.EventBase) -> None:
        """Handle the certificates invalidated event."""
        self._do_renew_certificate()

    def _do_renew_certificate(self) -> None:
        """Handle the event when certificate is unavailable."""
        if not self._get_server_name():
            return
        self._renew_certificate()

    def _on_certificate_available(self, event: tls_certificates.CertificateAvailableEvent) -> None:
        """Handle the certificate-available event.

        Args:
            event: certificate-available event object.
        """
        self.tls_keychain.set_chain(event.chain_as_pem().strip())
        self._configure_chrony()

    def _renew_certificate(self) -> None:
        """Renew the certificate.

        Raises:
            AssertionError: if there's no server name (canary exception).
        """
        old_csr = self.tls_keychain.get_csr()
        private_key = self.tls_keychain.get_private_key()
        if not self._get_server_name():  # pragma: nocover
            raise AssertionError("no server name")
        new_csr = tls_certificates.generate_csr(
            private_key=private_key.encode(),
            subject=self._get_server_name(),
            sans_dns=[self._get_server_name(), f"*.{self._get_server_name()}"],
        )
        if not old_csr:
            self.certificates.request_certificate_creation(certificate_signing_request=new_csr)
        else:
            self.certificates.request_certificate_renewal(
                old_certificate_signing_request=old_csr.encode(),
                new_certificate_signing_request=new_csr,
            )
        self.tls_keychain.set_server_name(self._get_server_name())
        self.tls_keychain.set_csr(new_csr.decode(encoding="ascii").strip())

    def _revoke_certificate(self) -> None:
        """Renew the certificate."""
        csr = self.tls_keychain.get_csr()
        if csr:
            self.certificates.request_certificate_revocation(csr.encode())
        self.tls_keychain.clear()

    def _on_install(self, _: ops.EventBase) -> None:
        """Handle install event."""
        self._do_install()

    def _on_upgrade_charm(self, _: ops.EventBase) -> None:
        """Handle upgrade-charm event."""
        self._do_install()

    def _do_install(self) -> None:
        """Install required packages and open NTP port."""
        self.unit.status = ops.MaintenanceStatus("installing chrony")
        self.chrony.install()
        self.unit.open_port("udp", 123)
        if not self.tls_keychain.get_private_key():
            self.tls_keychain.set_private_key(
                tls_certificates.generate_private_key().decode("ascii").strip()
            )

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle the "config-changed" event."""
        if (
            self._get_server_name()
            and self.model.get_relation("nts-certificates")
            and (
                not self.tls_keychain.get_key_pairs()
                or self.tls_keychain.get_server_name() != self._get_server_name()
            )
        ):
            self._renew_certificate()
        if not self._get_server_name() and self.tls_keychain.get_private_key():
            self._revoke_certificate()
        self._configure_chrony()

    def _on_secret_changed(self, event: ops.SecretChangedEvent) -> None:
        """Handle the "secret-changed" event for nts-certificates charm configuration.

        Args:
            event: secret-changed event object.
        """
        if typing.cast(str, event.secret.id) in typing.cast(
            str, self.config.get("nts-certificates")
        ):
            self._configure_chrony()

    def _configure_chrony(self) -> None:
        """Configure chrony."""
        sources = self._get_time_sources()
        if not sources:
            return
        if self._get_nts_certificates():
            self.unit.open_port("tcp", 4460)
        else:
            self.unit.close_port("tcp", 4460)
        self.chrony.new_config(sources=sources, tls_key_pairs=self._get_nts_certificates()).apply()

    def _get_server_name(self) -> str | None:
        """Get server name from charm configuration.

        Returns:
            The server name, None if not configured.
        """
        return typing.cast(str | None, self.config.get("server-name"))

    def _get_time_sources(self) -> list[TimeSource]:
        """Get time sources from charm configuration.

        Returns:
            Time source objects.
        """
        urls = typing.cast(str, self.config.get("sources"))
        return [
            self.chrony.parse_source_url(url.strip()) for url in urls.split(",") if url.strip()
        ]

    def _get_nts_certificates(self) -> list[TlsKeyPair]:
        """Get TLS certificates for NTS from charm configuration and tls-certificate integration.

        Returns:
            A list of TlsKeyPair objects.
        """
        certs = []
        for secret_id in typing.cast(str, self.config.get("nts-certificates")).split(","):
            secret_id = secret_id.strip()
            if not secret_id:
                continue
            secret = self.model.get_secret(id=secret_id)
            secret_value = secret.get_content(refresh=True)
            certs.append(TlsKeyPair(certificate=secret_value["cert"], key=secret_value["key"]))
        certs.extend(self.tls_keychain.get_key_pairs())
        return certs


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(ChronyCharm)

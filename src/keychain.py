# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""TLS credential storage management."""

import pathlib

from chrony import TlsKeyPair


class TlsKeychain:
    """Manage the storage and retrieval of TLS-related key materials for the charm.

    Attributes:
        STORAGE_DIR: The directory where TLS key materials are stored.
    """

    STORAGE_DIR = pathlib.Path("/var/lib/chrony-operator/tls-keychain")

    def __init__(self, namespace: str) -> None:
        """Initialize the TlsKeychain.

        Args:
            namespace: The storage namespace.
        """
        self._namespace = namespace

    def get_private_key(self) -> str | None:
        """Retrieve the private key from the storage.

        Returns:
            The private key as a string, or None if not found.
        """
        return self._get_file_content("private-key.pem")

    def set_private_key(self, private_key: str) -> None:
        """Store the private key into the storage.

        Args:
            private_key: The private key as a string to store.
        """
        self._storage_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self._storage_dir / "private-key.pem").write_text(private_key, encoding="utf-8")

    def get_server_name(self) -> str | None:
        """Retrieve the server name from the storage.

        Returns:
            The server name as a string, or None if not found.
        """
        return self._get_file_content("server-name")

    def set_server_name(self, server_name: str) -> None:
        """Store the server name into the storage.

        Args:
            server_name: The server name as a string to store.
        """
        self._storage_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self._storage_dir / "server-name").write_text(server_name, encoding="utf-8")

    def get_csr(self) -> str | None:
        """Retrieve the certificate signing request (CSR) from the storage.

        Returns:
            The CSR as a string, or None if not found.
        """
        return self._get_file_content("csr.pem")

    def set_csr(self, csr: str) -> None:
        """Store the certificate signing request (CSR) into the storage.

        Args:
            csr: The CSR as a string to store.
        """
        self._storage_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self._storage_dir / "csr.pem").write_text(csr, encoding="utf-8")

    def get_chain(self) -> str | None:
        """Retrieve the certificate chain from the storage.

        Returns:
            The certificate chain as a string, or None if not found.
        """
        return self._get_file_content("chain.pem")

    def set_chain(self, chain: str) -> None:
        """Store the certificate chain into the storage.

        Args:
            chain: The certificate chain as a string to store.
        """
        self._storage_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self._storage_dir / "chain.pem").write_text(chain, encoding="utf-8")

    def get_key_pairs(self) -> list[TlsKeyPair]:
        """Retrieve a list of TLS key pairs from the storage.

        Returns:
            A list of TlsKeyPair objects, or an empty list if no key pairs are found.
        """
        chain = self.get_chain()
        private_key = self.get_private_key()
        if chain and private_key:
            return [TlsKeyPair(certificate=chain, key=private_key)]
        return []

    def clear(self) -> None:
        """Clear all stored TLS key materials from the storage directory."""
        (self._storage_dir / "server-name").unlink(missing_ok=True)
        (self._storage_dir / "chain.pem").unlink(missing_ok=True)
        (self._storage_dir / "csr.pem").unlink(missing_ok=True)

    def _get_file_content(self, filename: str) -> str | None:
        """Retrieve the content of a specified file from keychain storage if it exists.

        Args:
            filename: The name of the file to retrieve.

        Returns:
            The content of the file as a string or None if the file does not exist.
        """
        file = self._storage_dir / filename
        if file.exists():
            return file.read_text(encoding="utf-8")
        return None

    @property
    def _storage_dir(self) -> pathlib.Path:
        """Get the namespaced storage directory.

        Returns:
            The namespaced storage directory.
        """
        return self.STORAGE_DIR / self._namespace

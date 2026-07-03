# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Chrony controller."""

# check chrony.conf document for _PoolOptions attributes.

import collections
import itertools
import logging
import os
import pathlib
import shutil
import textwrap
import typing
import urllib.parse

import pydantic
from charms.operator_libs_linux.v0 import apt
from charms.operator_libs_linux.v1 import systemd

logger = logging.getLogger(__name__)

_BIN_DIR = pathlib.Path(__file__).parent.parent / "bin"
_FILES_DIR = pathlib.Path(__file__).parent.parent / "files"
_CHRONY_EXPORTER_BIN_FILE = pathlib.Path("/usr/bin/chrony_exporter")
_CHRONY_EXPORTER_SERVICE_FILE = pathlib.Path(
    "/usr/lib/systemd/system/prometheus-chrony-exporter.service"
)
_CHRONY_EXPORTER_APPARMOR_FILE = pathlib.Path("/etc/apparmor.d/usr.bin.chrony_exporter")
_CHRONY_EXPORTER_FILES = {
    _BIN_DIR / "chrony_exporter": _CHRONY_EXPORTER_BIN_FILE,
    _FILES_DIR / "chrony-exporter.service": _CHRONY_EXPORTER_SERVICE_FILE,
    _FILES_DIR / "usr.bin.chrony_exporter": _CHRONY_EXPORTER_APPARMOR_FILE,
}
_CHRONY_EXPORTER_SERVICE_NAME = "prometheus-chrony-exporter"


class _PoolOptions(pydantic.BaseModel):
    """Chrony pool directive options.

    For more detail: https://chrony-project.org/doc/4.5/chrony.conf.html
    """

    model_config = pydantic.ConfigDict(extra="forbid")

    minpoll: int | None = None
    maxpoll: int | None = None
    iburst: bool = False
    burst: bool = False
    key: str | None = None
    nts: bool = False
    certset: str | None = None
    maxdelay: float | None = None
    maxdelayratio: float | None = None
    maxdelaydevratio: float | None = None
    maxdelayquant: float | None = None
    mindelay: float | None = None
    asymmetry: float | None = None
    offset: float | None = None
    minsamples: int | None = None
    maxsamples: int | None = None
    filter: int | None = None
    offline: bool = False
    auto_offline: bool = False
    prefer: bool = False
    noselect: bool = False
    trust: bool = False
    require: bool = False
    xleave: bool = False
    polltarget: int | None = None
    presend: int | None = None
    minstratum: int | None = None
    version: int | None = None
    extfield: str | None = None
    maxsources: int | None = None

    def render_options(self) -> str:
        """Render pool options as chrony option string.

        Returns:
            Chrony pool directive option string.
        """
        options = []
        # mypy and pylint have problems handling the model_fields class attribute.
        # pylint: disable=not-an-iterable
        for field in sorted(f for f in _PoolOptions.model_fields if f != "copy"):  # type: ignore
            value = getattr(self, field)
            # first, check if the value is of boolean type and True
            # then, check if the value is of boolean type and False or None (unset)
            # finally, check if the value is of a non-boolean type and set
            if value is True:
                options.append(field)
            elif value is None or value is False:
                continue
            else:
                options.extend([field, str(value)])
        return " ".join(options)


class _NtpSource(_PoolOptions):
    """A NTP time source."""

    host: typing.Annotated[str, pydantic.StringConstraints(min_length=1)]
    port: int | None = None

    @classmethod
    def from_source_url(cls, url: str) -> "_NtpSource":
        """Parse a NTP time source from a URL.

        Args:
            url: URL to parse.

        Returns:
            Parsed NTP time source.

        Raises:
            ValueError: If the URL is invalid.
        """
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "ntp":
            raise ValueError(f"Invalid NTP source URL: {url}")
        query = dict(urllib.parse.parse_qsl(parsed.query))
        return cls(host=parsed.hostname, port=parsed.port, **query)  # type: ignore

    def render(self) -> str:
        """Render NTP time source as a chrony pool directive string.

        Returns:
            Chrony pool directive string.
        """
        directive = f"pool {self.host}"
        if self.port is not None and self.port != 123:
            directive += f" port {self.port}"
        options = self.render_options()
        if options:
            directive += f" {options}"
        return directive


class _NtsSource(_PoolOptions):
    """A NTP time source with NTS enabled."""

    host: typing.Annotated[str, pydantic.StringConstraints(min_length=1)]
    ntsport: int | None = None

    @classmethod
    def from_source_url(cls, url: str) -> "_NtsSource":
        """Parse a NTP time source with NTS enabled from a URL.

        Args:
            url: URL to parse.

        Returns:
            Parsed NTP time source.

        Raises:
            ValueError: If the URL is invalid.
        """
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "nts":
            raise ValueError(f"Invalid NTS source URL: {url}")
        query = dict(urllib.parse.parse_qsl(parsed.query))
        return cls(host=parsed.hostname, ntsport=parsed.port, **query)  # type: ignore

    def render(self) -> str:
        """Render NTP time source as a chrony pool directive string with NTS enabled.

        Returns:
            Chrony pool directive string.
        """
        directive = f"pool {self.host} nts"
        if self.ntsport is not None and self.ntsport != 4460:
            directive += f" ntsport {self.ntsport}"
        options = self.render_options()
        if options:
            directive += f" {options}"
        return directive


TimeSource = _NtpSource | _NtsSource
TlsKeyPair = collections.namedtuple("TlsKeyPair", ["certificate", "key"])


class Chrony:
    """Chrony service manager."""

    CONFIG_FILE = pathlib.Path("/etc/chrony/chrony.conf")
    CONFIG_FILE_BACKUP = pathlib.Path("/var/lib/chrony/chrony.conf.bak")
    CERTS_DIR = pathlib.Path("/etc/chrony/certs")

    @staticmethod
    def is_installed() -> bool:
        """Check if chrony related packages is installed.

        Returns:
            True if installed, False otherwise.
        """
        if not shutil.which("chrony_exporter"):
            return False
        if not shutil.which("chronyc"):
            return False
        for source, target in _CHRONY_EXPORTER_FILES.items():
            if source.read_bytes() != target.read_bytes():
                return False
        return True

    def install(self) -> None:  # pragma: nocover
        """Install or upgrade Chrony on the system."""
        apt.add_package(
            ["chrony", "ca-certificates"],
            update_cache=True,
        )
        if not shutil.which("chrony_exporter"):
            self._install_chrony_exporter()
        else:
            self._upgrade_chrony_exporter()

    def uninstall(self) -> None:
        """Uninstall installed packages from the system.

        Not all packages will be uninstalled, as some are system defaults.
        For example, ca-certificates and chrony (as in Ubuntu 26.04).
        """
        self._uninstall_chrony_exporter()

    def read_config(self) -> str:
        """Read the current chrony configuration file.

        Returns:
            The current chrony configuration file content.
        """
        return self.CONFIG_FILE.read_text(encoding="utf-8")  # pragma: nocover

    def write_config(self, config: str) -> None:
        """Write the chrony configuration file.

        Args:
            config: The new chrony configuration file content.
        """
        self.CONFIG_FILE.write_text(config, encoding="utf-8")  # pragma: nocover

    def backup_config(self) -> None:
        """Backup the current chrony configuration file."""
        if self.CONFIG_FILE_BACKUP.exists():
            logger.warning("failed to backup configuration file: backup already exists")
            return
        self.CONFIG_FILE_BACKUP.write_text(self.read_config(), encoding="utf-8")

    def restore_config(self) -> None:
        """Restore the chrony configuration file from backup."""
        if not self.CONFIG_FILE_BACKUP.exists():
            logger.warning("failed to restore chrony configuration file from backup: no backup")
            return
        self.write_config(self.CONFIG_FILE_BACKUP.read_text(encoding="utf-8"))
        self.CONFIG_FILE_BACKUP.unlink()

    def _make_certs_dir(self) -> None:  # pragma: nocover
        """Create the chrony TLS certificates directory."""
        self.CERTS_DIR.mkdir(exist_ok=True, mode=0o700)
        shutil.chown(self.CERTS_DIR, "_chrony", "_chrony")

    def _iter_certs_dir(self) -> list[pathlib.Path]:  # pragma: nocover
        """Iterate over all certificate files in the certificate directory.

        Returns:
            An iterator over the paths of the certificate files.
        """
        return [f for f in self.CERTS_DIR.iterdir() if f.suffix in {".crt", ".key"}]

    @staticmethod
    def _write_certs_file(path: pathlib.Path, content: str) -> None:  # pragma: nocover
        """Write content of a certificate file and set appropriate permissions and ownership.

        Args:
            path: The path to the certificate file.
            content: The content to write to the file.
        """
        path.touch(mode=0o600, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        shutil.chown(path, "_chrony", "_chrony")

    @staticmethod
    def _read_certs_file(path: pathlib.Path) -> str:
        """Read and return the content of a certificate file.

        Args:
            path: The path to the certificate file.

        Returns:
            The content of the certificate file as a string.
        """
        return path.read_text(encoding="utf-8")  # pragma: nocover

    @staticmethod
    def _unlink_certs_file(path: pathlib.Path) -> None:
        """Unlink (delete) a certificate file.

        Args:
            path: The path to the certificate file to delete.
        """
        path.unlink(missing_ok=True)  # pragma: nocover

    def read_tls_key_pairs(self) -> list[TlsKeyPair]:
        """Read TLS key pairs from the certificates directory.

        Returns:
            A list of TlsKeyPair objects.
        """
        self._make_certs_dir()
        files = sorted(self._iter_certs_dir())
        key_pairs = []
        for crt, key in self._batched(files, 2):
            key_pairs.append(
                TlsKeyPair(
                    certificate=self._read_certs_file(crt),
                    key=self._read_certs_file(key),
                )
            )
        return key_pairs

    def _batched(self, iterable: typing.Iterable, n: int) -> typing.Iterable:
        """Batch data from the iterable into tuples of length n. The last may be shorter than n.

        Args:
              iterable: The iterable to batch.
              n: The number of elements to batch.

        Returns:
            An iterator over the tuples of length n.
        """
        if n < 1:
            raise ValueError("n must be at least one")
        iterator = iter(iterable)
        while batch := tuple(itertools.islice(iterator, n)):
            yield batch

    def write_tls_key_pairs(self, key_pairs: list[TlsKeyPair]) -> None:
        """Write TLS key pairs to the certificates directory.

        Existing pairs are overwritten, and if more files exist than new key pairs provided,
        the excess files are removed.

        Args:
            key_pairs: A list of TlsKeyPair objects to write.
        """
        self._make_certs_dir()
        files = sorted(self._iter_certs_dir())
        for idx, (key_pair_files, key_pair) in enumerate(
            itertools.zip_longest(self._batched(files, 2), key_pairs)
        ):
            if key_pair_files is None:
                self._write_certs_file(self.CERTS_DIR / f"{idx:04}.crt", key_pair.certificate)
                self._write_certs_file(self.CERTS_DIR / f"{idx:04}.key", key_pair.key)
                continue
            if key_pair is None:
                for file in key_pair_files:
                    self._unlink_certs_file(file)
                continue
            crt_file, key_file = key_pair_files
            if self._read_certs_file(crt_file) != key_pair.certificate:
                self._write_certs_file(crt_file, key_pair.certificate)
            if self._read_certs_file(key_file) != key_pair.key:
                self._write_certs_file(key_file, key_pair.key)

    @staticmethod
    def restart() -> None:
        """Restart the chrony service."""
        systemd.service_restart("chrony")  # pragma: nocover

    @staticmethod
    def parse_source_url(url: str) -> TimeSource:
        """Parse a time source from a URL.

        Args:
            url: URL to parse.

        Returns:
            Parsed TimeSource instance.

        Raises:
            ValueError: If the URL is invalid.
        """
        if url.startswith("ntp://"):
            return _NtpSource.from_source_url(url)
        if url.startswith("nts://"):
            return _NtsSource.from_source_url(url)
        raise ValueError(f"Invalid time source URL: {url}")

    @staticmethod
    def new_config(sources: list[TimeSource], header: str = "") -> str:
        """Generate the chrony configuration file content.

        Args:
            header: Optional header in the configuration file.
            sources: List of chrony time sources.

        Returns:
            Generated chrony configuration file content.

        Raises:
            ValueError: If no sources are provided.
        """
        if not sources:
            raise ValueError("No time sources provided")
        sources_config = "\n".join(s.render() for s in sources)
        static = textwrap.dedent("""\
                sourcedir /run/chrony-dhcp
                sourcedir /etc/chrony/sources.d
                keyfile /etc/chrony/chrony.keys
                driftfile /var/lib/chrony/chrony.drift
                ntsdumpdir /var/lib/chrony
                logdir /var/log/chrony
                maxupdateskew 100.0
                rtcsync
                makestep 1 3
                leapsectz right/UTC
            """)
        return "\n\n".join(part for part in [header, sources_config, static] if part).lstrip()

    def _install_chrony_exporter_files(self) -> None:
        """Install chrony_exporter files."""
        for source, dest in _CHRONY_EXPORTER_FILES.items():
            executable = os.access(source, os.X_OK)
            if executable:
                dest.unlink(missing_ok=True)
            shutil.copy(source, dest)
            os.chmod(dest, 0o755 if executable else 0o644)

    def _install_chrony_exporter(self) -> None:
        """Install chrony_exporter service."""
        self._install_chrony_exporter_files()
        systemd.service_reload("apparmor")
        systemd.service_enable(_CHRONY_EXPORTER_SERVICE_NAME)
        systemd.service_start(_CHRONY_EXPORTER_SERVICE_NAME)

    def _upgrade_chrony_exporter(self) -> None:
        self._install_chrony_exporter_files()
        systemd.daemon_reload()
        systemd.service_reload("apparmor")
        systemd.service_restart(_CHRONY_EXPORTER_SERVICE_NAME)

    def _uninstall_chrony_exporter(self) -> None:
        """Uninstall chrony_exporter service."""
        systemd.service_stop("prometheus-chrony-exporter")
        systemd.service_disable("prometheus-chrony-exporter")
        os.unlink(_CHRONY_EXPORTER_SERVICE_FILE)
        os.unlink(_CHRONY_EXPORTER_APPARMOR_FILE)
        systemd.service_reload("apparmor")
        os.unlink(_CHRONY_EXPORTER_BIN_FILE)

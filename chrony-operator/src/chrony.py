# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Chrony controller."""

# check chrony.conf document for _PoolOptions attributes.

import collections
import itertools
import logging
import pathlib
import shutil
import subprocess  # nosec
import textwrap
import typing
import urllib.parse

import pydantic
from charms.operator_libs_linux.v0 import apt
from charms.operator_libs_linux.v1 import systemd

logger = logging.getLogger(__name__)


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


class _ChronyConfig:
    """Chrony configuration file control."""

    def __init__(
        self,
        chrony: "Chrony",
        sources: list[TimeSource],
        tls_key_pairs: list[TlsKeyPair] | None = None,
    ) -> None:
        """Initialize chrony configuration object.

        Args:
            chrony: Chrony controller.
            sources: List of chrony time sources.
            tls_key_pairs: List of TLS key pairs.
        """
        self._chrony = chrony
        self._sources = sources
        self._tls_key_pairs = tls_key_pairs if tls_key_pairs else []

    def render(self) -> str:
        """Generate the chrony configuration file content.

        Returns:
            Generated chrony configuration file content.
        """
        sources = "\n".join(s.render() for s in self._sources)
        certs_lines = []
        for idx, _ in enumerate(self._tls_key_pairs):
            certs_lines.append(
                "ntsservercert " + str((self._chrony.CERTS_DIR / f"{idx:04}.crt").absolute())
            )
            certs_lines.append(
                "ntsserverkey " + str((self._chrony.CERTS_DIR / f"{idx:04}.key").absolute())
            )
        certs = "\n".join(certs_lines)
        static = textwrap.dedent(
            """\
                bindcmdaddress 127.0.0.1
                driftfile /var/lib/chrony/chrony.drift
                ntsdumpdir /var/lib/chrony
                logdir /var/log/chrony
                maxupdateskew 100.0
                rtcsync
                makestep 1 3
                leapsectz right/UTC
                allow 0.0.0.0/0
                allow ::/0
                """
        )
        return "\n\n".join(part for part in [sources, certs, static] if part)

    def apply(self) -> None:
        """Apply the new chrony configuration.

        This function compares the current chrony configuration with a new configuration. If they
        are the same, no changes are made. If they differ, the function updates the chrony
        configuration file with the new settings and restarts the chrony service.
        """
        current_config = self._chrony.read_config()
        current_certs = self._chrony.read_tls_key_pairs()
        new_config = self.render()
        if new_config != current_config or current_certs != self._tls_key_pairs:
            logger.info("Chrony config changed, apply and restart chrony")
            self._chrony.write_tls_key_pairs(self._tls_key_pairs)
            self._chrony.write_config(new_config)
            self._chrony.restart()


class Chrony:
    """Chrony service manager."""

    CONFIG_FILE = pathlib.Path("/etc/chrony/chrony.conf")
    CERTS_DIR = pathlib.Path("/etc/chrony/certs")

    @staticmethod
    def install() -> None:  # pragma: nocover
        """Install the Chrony on the system."""
        subprocess.check_call(["add-apt-repository", "-y", "ppa:canonical-is-devops/chrony-charm"])  # nosec  # noqa: S607
        apt.add_package(
            ["chrony", "ca-certificates", "prometheus-chrony-exporter"], update_cache=True
        )

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
        for crt, key in itertools.batched(files, 2):
            key_pairs.append(
                TlsKeyPair(
                    certificate=self._read_certs_file(crt),
                    key=self._read_certs_file(key),
                )
            )
        return key_pairs

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
            itertools.zip_longest(itertools.batched(files, 2), key_pairs)
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

    def new_config(
        self,
        *,
        sources: list[TimeSource],
        tls_key_pairs: list[TlsKeyPair] | None = None,
    ) -> _ChronyConfig:
        """Create a new chrony configuration object.

        Args:
            sources: A list of time sources to be used by chrony.
            tls_key_pairs: The TLS credentials to use to enable NTS.

        Returns:
            Chrony configuration object.

        Raises:
            ValueError: If the URL is invalid.
        """
        if not sources:
            raise ValueError("No time sources provided")
        return _ChronyConfig(chrony=self, sources=sources, tls_key_pairs=tls_key_pairs)

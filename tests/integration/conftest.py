# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm integration tests."""

import pathlib
import platform
import typing

import jubilant
import pytest
import yaml
from opcli.pytest_plugin import CharmPathList

_CHARMCRAFT_YAML = pathlib.Path(__file__).parents[2] / "chrony-client-operator" / "charmcraft.yaml"
_CODENAMES = {"22.04": "jammy", "24.04": "noble", "26.04": "resolute"}


def _current_arch() -> str:
    """Get the Debian architecture name of the current machine.

    Returns:
        The architecture name, e.g. amd64, arm64, s390x or ppc64el.
    """
    machine = platform.machine().lower()
    return {
        "x86_64": "amd64",
        "aarch64": "arm64",
        "ppc64le": "ppc64el",
    }.get(machine, machine)


def _supported_bases() -> list[str]:
    """Get the bases declared in charmcraft.yaml for the current architecture.

    Returns:
        Sorted list of bases, e.g. ["ubuntu@22.04", "ubuntu@24.04"].
    """
    platforms = yaml.safe_load(_CHARMCRAFT_YAML.read_text(encoding="utf-8"))["platforms"]
    bases = set()
    for platform_name in platforms:
        base, _, arch = platform_name.partition(":")
        if arch == _current_arch():
            bases.add(base)
    return sorted(bases)


def _app_suffix(base: str) -> str:
    """Get a juju application name suffix for a base.

    Args:
        base: The base, e.g. ubuntu@24.04.

    Returns:
        The suffix, e.g. noble.
    """
    version = base.partition("@")[2]
    return _CODENAMES.get(version, "base" + version.replace(".", ""))


@pytest.fixture(name="juju", scope="module")
def juju_fixture(request: pytest.FixtureRequest) -> typing.Generator[jubilant.Juju, None, None]:
    """Pytest fixture that wraps :meth:`jubilant.with_model`."""

    def show_debug_log(juju: jubilant.Juju) -> None:
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")

    use_existing = request.config.getoption("--use-existing", default=False)
    if use_existing:
        juju = jubilant.Juju()
        yield juju
        show_debug_log(juju)
        return

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        yield juju
        show_debug_log(juju)
        return

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        yield juju
        show_debug_log(juju)
        return


@pytest.fixture(name="chrony_client_charm_files", scope="session")
def chrony_client_charm_files_fixture(charm_paths: dict[str, CharmPathList]) -> dict[str, str]:
    """Get the chrony-client charm files for the current architecture, keyed by base."""
    paths = charm_paths["chrony-client"]
    return {base: path for base, path in zip(paths.bases, paths, strict=True) if base is not None}


@pytest.fixture(name="deploy_charms", scope="module")
def deploy_charms_fixture(juju: jubilant.Juju, chrony_client_charm_files: dict[str, str]):
    """Deploy a principle and a chrony-client charm for every available base."""
    for base, charm_file in chrony_client_charm_files.items():
        suffix = _app_suffix(base)
        juju.deploy(charm="ubuntu", app=f"ubuntu-{suffix}", base=base, channel="latest/edge")
        juju.deploy(charm=charm_file, app=f"chrony-client-{suffix}")
        juju.integrate(f"ubuntu-{suffix}", f"chrony-client-{suffix}")
    if _current_arch() == "amd64":
        juju.deploy(
            charm="chrony",
            config={"sources": "ntp://ntp.ubuntu.com?iburst=true&maxsources=4"},
            channel="latest/edge",
        )
    else:
        juju.deploy(charm="ubuntu", app="chrony", base="ubuntu@24.04", channel="latest/edge")
    juju.wait(jubilant.all_active, timeout=20 * 60)
    if _current_arch() != "amd64":
        juju.exec(
            "set -e; "
            "apt-get update; "
            "DEBIAN_FRONTEND=noninteractive apt-get install -y chrony; "
            "printf 'allow all\\nlocal stratum 10\\n' > /etc/chrony/conf.d/server.conf; "
            "systemctl restart chrony",
            unit="chrony/leader",
            wait=10 * 60,
        )


@pytest.fixture(name="base", scope="module", params=_supported_bases())
def base_fixture(request: pytest.FixtureRequest, chrony_client_charm_files: dict[str, str]):
    """The charm base under test; skipped if no charm was built for it."""
    if request.param not in chrony_client_charm_files:
        pytest.skip(f"no chrony-client charm built for {request.param} on {_current_arch()}")
    return request.param


class App:
    """A helper class for charm applications."""

    def __init__(self, juju: jubilant.Juju, name: str) -> None:
        """Initialize the charm application class.

        Args:
            juju: Juju instance
            name: Application name
        """
        self._juju = juju
        self.name = name

    def get_leader_unit(self) -> str:
        """Get the leader unit name for this application.

        Returns:
            Leader unit name.

        Raises:
            RuntimeError: If no leader unit exists for this application.
        """
        status = self._juju.status()
        leader = [name for name, unit in status.get_units(self.name).items() if unit.leader]
        if not leader:
            raise RuntimeError(f"no leader unit found for {self.name}?")
        return leader[0]

    def get_unit_ip(self, unit_num: int | None = None) -> str:
        """Get the IP address of the unit.

        Args:
            unit_num: unit number, if not provided, the leader unit number is used.

        Returns:
            IP address of the unit.
        """
        status = self._juju.status()
        units = status.get_units(self.name)
        unit_name = self.get_leader_unit() if unit_num is None else f"{self.name}/{unit_num}"
        unit_ip = units[unit_name].public_address
        return unit_ip

    def ssh(self, cmd: str, *, unit_num: int | None = None) -> str:
        """Run a command on a charm unit.

        Args:
            cmd: command to run
            unit_num: unit number, if not provided, the leader unit number is used.

        Returns:
            Output of the command.
        """
        unit_name = self.get_leader_unit() if unit_num is None else f"{self.name}/{unit_num}"
        return self._juju.ssh(target=unit_name, command=cmd)


@pytest.fixture(scope="module", name="principle_app")
def principle_app_fixture(
    juju: jubilant.Juju,
    base: str,
    # pylint: disable=unused-argument
    deploy_charms,
):
    """Deployed principle charm app for the base under test."""
    return App(juju=juju, name=f"ubuntu-{_app_suffix(base)}")


@pytest.fixture(scope="module", name="chrony_client_app")
def chrony_client_app_fixture(
    juju: jubilant.Juju,
    base: str,
    # pylint: disable=unused-argument
    deploy_charms,
) -> App:
    """Deployed chrony-client charm app for the base under test."""
    return App(juju=juju, name=f"chrony-client-{_app_suffix(base)}")


@pytest.fixture(scope="module")
def chrony_app(
    juju: jubilant.Juju,
    # pylint: disable=unused-argument
    deploy_charms,
) -> App:
    """Deployed chrony charm app."""
    return App(juju=juju, name="chrony")


@pytest.fixture(scope="function")
def another_chrony_client_app(
    juju: jubilant.Juju,
    base: str,
    chrony_client_app,
    chrony_client_charm_files: dict[str, str],
    principle_app: App,
):
    """Deploy another chrony-client charm app on the principle of the base under test."""
    name = f"another-chrony-client-{_app_suffix(base)}"

    juju.deploy(charm=chrony_client_charm_files[base], app=name)
    juju.integrate(principle_app.name, name)
    juju.wait(jubilant.all_agents_idle, timeout=20 * 60)

    yield App(juju=juju, name=name)

    juju.remove_application(name, force=True)
    juju.wait(lambda status: name not in status.apps, timeout=20 * 60)

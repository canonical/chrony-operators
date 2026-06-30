# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm integration tests."""

import typing

import jubilant
import pytest
from opcli.pytest_plugin import CharmPathList


@pytest.fixture(name="chrony_client_charm_file", scope="session")
def chrony_client_charm_file_fixture(charm_paths: dict[str, CharmPathList]):
    """Get the chrony-client charm file built for the 24.04 base."""
    return charm_paths["chrony-client"]["ubuntu@24.04"]


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


@pytest.fixture(name="deploy_charms", scope="module")
def deploy_charms_fixture(juju: jubilant.Juju, chrony_client_charm_file: str):
    """Deploy charms fixture deploy all charms necessary for the integration test."""
    juju.deploy(
        charm="ubuntu",
        base="ubuntu@24.04",
        constraints={"virt-type": "virtual-machine"},
    )
    juju.deploy(charm=chrony_client_charm_file)
    juju.deploy(
        charm="chrony",
        config={"sources": "ntp://ntp.ubuntu.com?iburst=true&maxsources=4"},
        channel="latest/edge",
        constraints={"virt-type": "virtual-machine"},
    )
    juju.integrate("ubuntu", "chrony-client")
    juju.wait(jubilant.all_active, timeout=20 * 60)


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
    # pylint: disable=unused-argument
    deploy_charms,
):
    """Deploy the principle charm app."""
    return App(juju=juju, name="ubuntu")


@pytest.fixture(scope="module", name="chrony_client_app")
def chrony_client_app_fixture(
    juju: jubilant.Juju,
    # pylint: disable=unused-argument
    deploy_charms,
) -> App:
    """Deployed chrony-client charm app."""
    return App(juju=juju, name="chrony-client")


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
    chrony_client_app,
    chrony_client_charm_file,
    # pylint: disable=unused-argument
    principle_app,
):
    """Deploy another chrony-client charm app."""
    name = "another-chrony-client"

    juju.deploy(charm=chrony_client_charm_file, app=name)
    juju.integrate("ubuntu", name)
    juju.wait(jubilant.all_agents_idle, timeout=20 * 60)

    yield App(juju=juju, name=name)

    juju.remove_application(name)

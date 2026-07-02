# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test fixtures."""

import logging
from collections.abc import Callable, Generator

import jubilant
import pytest
from opcli.pytest_plugin import CharmPathList

JUJU_WAIT_TIMEOUT = 20 * 60  # 20 minutes
CHRONY_APP = "chrony"
SELF_SIGNED_CERTIFICATES_APP = "self-signed-certificates"
logger = logging.getLogger(__name__)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the spread/opcli integration options.

    Args:
        parser: Pytest argument parser.
    """
    parser.addoption("--model", action="store", default=None)
    parser.addoption("--keep-models", action="store_true", default=False)


@pytest.fixture(scope="module", name="juju")
def juju_fixture(request: pytest.FixtureRequest) -> Generator[jubilant.Juju, None, None]:
    """Jubilant juju fixture wrapping the spread-provided or a temporary model."""

    def show_debug_log(juju: jubilant.Juju) -> None:
        if request.session.testsfailed:
            print(juju.cli("status", "--relations"), end="")
            print(juju.debug_log(limit=1000), end="")

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju
        show_debug_log(juju)
        return
    keep_models = bool(request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju
        show_debug_log(juju)


@pytest.fixture(scope="module", name="chrony_app")
def chrony_app_fixture(juju: jubilant.Juju, charm_paths: dict[str, CharmPathList]) -> str:
    """Deploy the chrony charm and return its application name."""
    juju.deploy(charm_paths[CHRONY_APP].path, app=CHRONY_APP)
    juju.wait(jubilant.all_agents_idle, timeout=JUJU_WAIT_TIMEOUT)
    return CHRONY_APP


@pytest.fixture(scope="module", name="self_signed_certificates_app")
def self_signed_certificates_app_fixture(juju: jubilant.Juju) -> str:
    """Deploy the self-signed-certificates charm and return its application name."""
    juju.deploy(
        "self-signed-certificates",
        app=SELF_SIGNED_CERTIFICATES_APP,
        channel="latest/stable",
    )
    juju.wait(jubilant.all_agents_idle, timeout=JUJU_WAIT_TIMEOUT)
    return SELF_SIGNED_CERTIFICATES_APP


@pytest.fixture(name="get_unit_ips")
def get_unit_ips_fixture(juju: jubilant.Juju) -> Callable[..., list[str]]:
    """A function to get unit ips of a charm application."""

    def _get_unit_ips(name: str = CHRONY_APP) -> list[str]:
        units = juju.status().get_units(name)
        return [
            units[key].public_address for key in sorted(units, key=lambda n: int(n.split("/")[-1]))
        ]

    return _get_unit_ips

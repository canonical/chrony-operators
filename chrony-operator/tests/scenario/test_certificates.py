# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Scenario tests."""

import copy
import json
import typing

import pytest
from charms.tls_certificates_interface.v3 import tls_certificates
from ops.testing import CharmEvents, Context, Relation, Secret, State
from scenario.context import _Event  # needed for custom events for now

from src.charm import ChronyCharm
from tests.utils import get_csr_common_name


@pytest.mark.usefixtures("mock_chrony")
def test_csr_created_after_nts_certificates_integration(mock_tls_keychain):
    """
    arrange: private key is set and a nts-certificates relation is created.
    act: trigger the 'nts-certificates-relation-created' event and handle it.
    assert: check if the CSR data is present in the relation's local unit data.
    """
    mock_tls_keychain.set_private_key(tls_certificates.generate_private_key().decode("ascii"))
    ctx = Context(ChronyCharm)
    relation = Relation("nts-certificates")
    state_in = State(config={"server-name": "example.com"}, relations=[relation])

    state_out = ctx.run(_Event("nts-certificates-relation-created", relation=relation), state_in)

    assert typing.cast(dict, state_out.get_relation(relation.id).local_unit_data)[
        "certificate_signing_requests"
    ]


@pytest.mark.usefixtures("mock_chrony")
def test_csr_not_created_if_server_name_unset(mock_tls_keychain):
    """
    arrange: without a server-name set in the configuration.
    act: trigger the 'nts-certificates-relation-created' event.
    assert: ensure that no certificate_signing_requests are created due to unset server-name.
    """
    mock_tls_keychain.set_private_key(tls_certificates.generate_private_key().decode("ascii"))
    ctx = Context(ChronyCharm)
    relation = Relation("nts-certificates")
    state_in = State(relations=[relation])

    state_out = ctx.run(_Event("nts-certificates-relation-created", relation=relation), state_in)

    assert "certificate_signing_requests" not in typing.cast(
        dict, state_out.get_relation(relation.id).local_unit_data
    )


@pytest.mark.usefixtures("mock_chrony")
def test_csr_created_after_server_name_set(mock_tls_keychain):
    """
    arrange: set a server-name and a private key and initialize a nts-certificates integration.
    act: simulate a config-changed event.
    assert: verify that certificate_signing_requests are generated.
    """
    mock_tls_keychain.set_private_key(tls_certificates.generate_private_key().decode("ascii"))
    ctx = Context(ChronyCharm)
    relation = Relation("nts-certificates")
    state_in = State(config={"server-name": "example.com"}, relations=[relation])

    state_out = ctx.run(CharmEvents.config_changed(), state_in)

    assert typing.cast(dict, state_out.get_relation(relation.id).local_unit_data)[
        "certificate_signing_requests"
    ]


def test_receive_certificate(mock_chrony, helper):
    """
    arrange: set server-name, csr, and establish provider side of nts-certificates integration.
    act: handle a 'nts-certificates-relation-changed' event.
    assert: confirm that certificates are received and stored correctly in the configuration.
    """
    helper.write_server_name_and_csr()
    relation = Relation(
        "nts-certificates",
        local_unit_data=helper.get_local_unit_data(),
        remote_app_data=helper.get_remote_app_data(),
    )
    ctx = Context(ChronyCharm)
    state_in = State(
        config={"server-name": "example.com", "sources": "ntp://example.com"}, relations=[relation]
    )

    ctx.run(_Event("nts-certificates-relation-changed", relation=relation), state_in)

    assert helper.tls_keychain.get_chain()
    assert len(mock_chrony.read_tls_key_pairs()) == 1
    assert "ntsservercert" in mock_chrony.read_config()
    assert "ntsserverkey" in mock_chrony.read_config()


def test_server_name_reset_after_certificates(mock_chrony, helper):
    """
    arrange: set up a scenario with certificates received from provider.
    act: change configuration settings to an empty server names.
    assert: verify certificates are cleared appropriately after config change.
    """
    helper.write_server_name_and_csr()
    helper.write_chain()
    relation = Relation(
        "nts-certificates",
        local_unit_data=helper.get_local_unit_data(),
        remote_app_data=helper.get_remote_app_data(),
    )
    secret = helper.get_tls_certificates_secret()
    ctx = Context(ChronyCharm)
    state_in = State(
        config={"sources": "ntp://example.com"}, relations=[relation], secrets=[secret]
    )

    state_out = ctx.run(CharmEvents.config_changed(), state_in)

    assert "ntsservercert" not in mock_chrony.read_config()
    assert not helper.tls_keychain.get_chain()
    assert not json.loads(
        typing.cast(dict, state_out.get_relation(relation.id).local_unit_data)[
            "certificate_signing_requests"
        ]
    )


def test_server_name_change_after_certificate_assigned(mock_chrony, helper):
    """
    arrange: set up a scenario with certificates received from provider.
    act: simulate a config-changed event with new different server-name.
    assert: check that the new CSR reflects the updated server-name correctly.
    """
    helper.write_server_name_and_csr()
    helper.write_chain()
    relation = Relation(
        "nts-certificates",
        local_unit_data=helper.get_local_unit_data(),
        remote_app_data=helper.get_remote_app_data(),
    )
    ctx = Context(ChronyCharm)
    state_in = State(
        config={"sources": "ntp://example.com", "server-name": "example.net"},
        relations=[relation],
        secrets=[helper.get_tls_certificates_secret()],
    )

    state_out = ctx.run(CharmEvents.config_changed(), state_in)

    assert "ntsservercert" in mock_chrony.read_config()
    csr = json.loads(
        typing.cast(dict, state_out.get_relation(relation.id).local_unit_data)[
            "certificate_signing_requests"
        ]
    )
    assert get_csr_common_name(csr[0]["certificate_signing_request"]) == "example.net"


def test_server_name_change_before_certificates_assigned(helper):
    """
    arrange: set up a scenario with CSR created without any certificates assigned.
    act: simulate a config-changed event to update the server-name.
    assert: check that the CSR reflects the updated server-name correctly.
    """
    helper.write_server_name_and_csr()
    relation = Relation(
        "nts-certificates",
        local_unit_data=helper.get_local_unit_data(),
    )
    ctx = Context(ChronyCharm)
    state_in = State(
        config={"sources": "ntp://example.com", "server-name": "example.net"},
        relations=[relation],
    )

    state_out = ctx.run(CharmEvents.config_changed(), state_in)
    csr = json.loads(
        typing.cast(dict, state_out.get_relation(relation.id).local_unit_data)[
            "certificate_signing_requests"
        ]
    )
    assert get_csr_common_name(csr[0]["certificate_signing_request"]) == "example.net"


def test_certificate_expired(monkeypatch, helper):
    """
    arrange: set up a scenario with certificates received from provider.
    act: simulate an 'secret-expired' event to trigger the renewal process.
    assert: ensure that a new CSR is requested to replace the expired one.
    """
    helper.write_server_name_and_csr()
    helper.write_chain()
    local_unit_data = helper.get_local_unit_data()
    relation = Relation(
        "nts-certificates",
        local_unit_data=copy.deepcopy(local_unit_data),
        remote_app_data=helper.get_remote_app_data(),
    )
    ctx = Context(ChronyCharm)
    secret = helper.get_tls_certificates_secret()
    state_in = State(
        config={"sources": "ntp://example.com", "server-name": "example.net"},
        relations=[relation],
        secrets=[secret],
    )

    monkeypatch.setenv("JUJU_SECRET_REVISION", "0")
    state_out = ctx.run(CharmEvents.secret_expired(secret, revision=0), state_in)
    assert (
        typing.cast(dict, state_out.get_relation(relation.id).local_unit_data)[
            "certificate_signing_requests"
        ]
        != local_unit_data["certificate_signing_requests"]
    )


def test_certificate_revoked(helper):
    """
    arrange: set up a scenario with certificates received from provider.
    act: simulate a relation change event indicating certificate revocation.
    assert: check if a new CSR is requested after the revocation is processed.
    """
    helper.write_server_name_and_csr()
    helper.write_chain()
    local_unit_data = helper.get_local_unit_data()
    relation = Relation(
        "nts-certificates",
        local_unit_data=copy.deepcopy(local_unit_data),
        remote_app_data=helper.get_revoked_remote_app_data(),
    )
    ctx = Context(ChronyCharm)
    secret = helper.get_tls_certificates_secret()
    state_in = State(
        config={"sources": "ntp://example.com", "server-name": "example.net"},
        relations=[relation],
        secrets=[secret],
    )

    state_out = ctx.run(CharmEvents.relation_changed(relation), state_in)

    assert (
        typing.cast(dict, state_out.get_relation(relation.id).local_unit_data)[
            "certificate_signing_requests"
        ]
        != local_unit_data["certificate_signing_requests"]
    )


def test_remove_certificate_integration(mock_chrony, helper):
    """
    arrange: set up a scenario with certificates received from provider.
    act: simulate a relation broken event to process certificate removal.
    assert: verify that all certificate data is cleared from configuration.
    """
    helper.write_server_name_and_csr()
    helper.write_chain()
    ctx = Context(ChronyCharm)
    secret = helper.get_tls_certificates_secret()
    relation = Relation(
        "nts-certificates",
        local_unit_data=helper.get_local_unit_data(),
    )
    state_in = State(
        config={"sources": "ntp://example.com", "server-name": "example.net"},
        relations=[relation],
        secrets=[secret],
    )
    assert helper.tls_keychain.get_chain()

    ctx.run(CharmEvents.relation_broken(relation), state_in)

    assert not helper.tls_keychain.get_chain()
    assert "ntsservercert" not in mock_chrony.read_config()
    assert "ntsserverkey" not in mock_chrony.read_config()


def test_nts_certificates_config(helper):
    """
    arrange: create a user provided secret to be set in nts-certificates charm configuration.
    act: process a config-changed event to set nts-certificates charm configuration.
    assert: confirm that the test certificates and keys are correctly used.
    """
    ctx = Context(ChronyCharm)
    secret_id = "secret:user-provided"
    secret = Secret(
        id=secret_id,
        tracked_content={"cert": "test cert", "key": "test key"},
    )
    state_in = State(
        config={"sources": "ntp://example.com", "nts-certificates": secret_id},
        secrets=[secret],
    )

    ctx.run(CharmEvents.config_changed(), state_in)

    assert "ntsservercert" in helper.chrony.read_config()
    assert "ntsserverkey" in helper.chrony.read_config()
    assert len(helper.chrony.read_tls_key_pairs()) == 1
    assert helper.chrony.read_tls_key_pairs()[0].certificate == "test cert"
    assert helper.chrony.read_tls_key_pairs()[0].key == "test key"


def test_nts_certificates_config_with_nts_certificates_integration(helper):
    """
    arrange: set up a scenario with certificates received from nts-certificates integration.
    act: handle a config-changed event to add a new nts-certificates charm configuration.
    assert: verify that the server configurations reflect the multiple certificates correctly.
    """
    helper.write_server_name_and_csr()
    helper.write_chain()
    local_unit_data = helper.get_local_unit_data()
    relation = Relation(
        "nts-certificates",
        local_unit_data=local_unit_data,
        remote_app_data=helper.get_remote_app_data(),
    )
    ctx = Context(ChronyCharm)
    integration_secret = helper.get_tls_certificates_secret()
    config_secret_id = "secret:user-provided"
    config_secret = Secret(
        id=config_secret_id,
        tracked_content={"cert": "test cert", "key": "test key"},
    )
    state_in = State(
        config={
            "sources": "ntp://example.com",
            "server-name": "example.net",
            "nts-certificates": config_secret_id,
        },
        relations=[relation],
        secrets=[integration_secret, config_secret],
    )

    ctx.run(CharmEvents.config_changed(), state_in)

    assert helper.chrony.read_config().count("ntsservercert") == 2
    assert helper.chrony.read_config().count("ntsserverkey") == 2

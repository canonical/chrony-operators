# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test utils."""

import collections
import datetime
import socket
import ssl
import time
import typing

import cryptography.hazmat.primitives.asymmetric.ec
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.serialization
import cryptography.x509
import cryptography.x509.oid


def gen_tls_certificate(server_name: str):
    """Generate a TLS certificate."""
    private_key = cryptography.hazmat.primitives.asymmetric.ec.generate_private_key(
        cryptography.hazmat.primitives.asymmetric.ec.SECP256R1()
    )
    certificate = (
        cryptography.x509.CertificateBuilder()
        .subject_name(
            cryptography.x509.Name(
                [
                    cryptography.x509.NameAttribute(
                        cryptography.x509.oid.NameOID.COMMON_NAME, server_name
                    )
                ]
            )
        )
        .issuer_name(
            cryptography.x509.Name(
                [
                    cryptography.x509.NameAttribute(
                        cryptography.x509.oid.NameOID.COMMON_NAME, server_name
                    )
                ]
            )
        )
        .public_key(private_key.public_key())
        .serial_number(cryptography.x509.random_serial_number())
        .not_valid_before(datetime.datetime(1950, 1, 1, tzinfo=datetime.timezone.utc))
        .not_valid_after(datetime.datetime(2950, 1, 1, tzinfo=datetime.timezone.utc))
        .add_extension(
            cryptography.x509.SubjectAlternativeName([cryptography.x509.DNSName(server_name)]),
            critical=False,
        )
        .sign(private_key, cryptography.hazmat.primitives.hashes.SHA256())
    )
    cert_pem = certificate.public_bytes(
        cryptography.hazmat.primitives.serialization.Encoding.PEM
    ).decode("ascii")
    key_pem = private_key.private_bytes(
        cryptography.hazmat.primitives.serialization.Encoding.PEM,
        cryptography.hazmat.primitives.serialization.PrivateFormat.PKCS8,
        cryptography.hazmat.primitives.serialization.NoEncryption(),
    ).decode("ascii")
    Certificate = collections.namedtuple("Certificate", "server_name cert cert_pem key key_pem")
    return Certificate(
        server_name=server_name,
        cert=certificate,
        cert_pem=cert_pem,
        key=private_key,
        key_pem=key_pem,
    )


def get_tls_certificates(
    host, port=4460, server_name=None, verify=True, cadata=None, timeout=60.0
) -> cryptography.x509.Certificate:
    """Retrieve the TLS certificate from a specified TLS server.

    Transient connection failures are retried until *timeout* seconds elapse.
    chrony restarts its NTS-KE server asynchronously after a config change, so
    the port may briefly refuse connections or drop the TLS handshake even once
    the Juju unit reports active/idle. Certificate verification failures are not
    transient and are raised immediately without retrying.
    """
    context = ssl.create_default_context(cadata=cadata)
    # Enforce secure TLS versions only (TLS 1.2 and above)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    if not verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    server_name = host if server_name is None else server_name
    deadline = time.monotonic() + timeout
    while True:
        try:
            with (
                socket.create_connection((host, port), timeout=30) as sock,
                context.wrap_socket(sock, server_hostname=server_name) as ssock,
            ):
                return cryptography.x509.load_der_x509_certificate(
                    typing.cast(bytes, ssock.getpeercert(binary_form=True))
                )
        except ssl.SSLCertVerificationError:
            raise
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)


def get_sans(certificate: cryptography.x509.Certificate) -> list[str]:
    """Extract the Subject Alternative Names (SANs) from a given X.509 certificate."""
    san_extension = certificate.extensions.get_extension_for_oid(
        cryptography.x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
    )
    return san_extension.value.get_values_for_type(cryptography.x509.DNSName)  # type: ignore


def get_common_name(certificate: cryptography.x509.Certificate) -> str:
    """Extract the common name from a given X.509 certificate subject."""
    subject = certificate.subject
    common_name_oid = cryptography.x509.oid.NameOID.COMMON_NAME
    return subject.get_attributes_for_oid(common_name_oid)[0].value  # type: ignore

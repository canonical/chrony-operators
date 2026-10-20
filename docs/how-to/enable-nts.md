<!-- vale Canonical.007-Headings-sentence-case = NO -->
# How to enable Network Time Security
<!-- vale Canonical.007-Headings-sentence-case = YES -->

Network Time Security (NTS) is a mechanism that uses Transport Layer Security
(TLS) and Authenticated Encryption with Associated Data (AEAD) to provide 
cryptographic security for the client-server mode of the Network Time Protocol
(NTP).

When a TLS certificate is provided to the Chrony charm, Chrony will 
automatically enable NTS, allowing NTS-capable NTP clients to securely
communicate with the Chrony charm. 
You can use one of the following options to configure the TLS certificate
used for NTS.

## `tls-certificates` integration

The Chrony charm can integrate with any charm that provides `tls-certificates` 
integration, such as the [`lego`](https://charmhub.io/lego) or 
[`self-signed-certificates`](https://charmhub.io/self-signed-certificates) 
charms. 
Refer to the respective `tls-certificates` provider charm's documentation 
for setup instructions. 
Once set up, you can integrate the `tls-certificates` provider charm with 
the Chrony charm using the `juju integrate` command:

```
juju integrate chrony:nts-certificates self-signed-certificates
```

## `nts-certificates` charm configuration

The Chrony charm includes a configuration option, `nts-certificates`, which 
can be used to provide existing TLS certificates directly to the Chrony 
charm. This is especially useful if you want to generate a 
[TLS certificate with an extended validity period for use with NTS clients lacking a real-time clock](https://chrony-project.org/faq.html#_using_nts). 

The TLS certificate must be stored in [a Juju user secret](https://juju.is/docs/juju/manage-secrets#add-a-secret) 
before being passed to the Chrony charm.

```
juju add-secret my-tls-cert cert#file=/path/to/fullchain.pem key#file=/path/to/key.pem
juju grant-secret my-tls-cert chrony
juju config chrony nts-certificates=<output from juju add-secret>
```
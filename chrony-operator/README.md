# Chrony charm

[![CharmHub Badge](https://charmhub.io/chrony/badge.svg)](https://charmhub.io/chrony)
[![Publish to edge](https://github.com/canonical/chrony-operator/actions/workflows/publish_charm.yaml/badge.svg)](https://github.com/canonical/chrony-operator/actions/workflows/publish_charm.yaml)
[![Promote charm](https://github.com/canonical/chrony-operator/actions/workflows/promote_charm.yaml/badge.svg)](https://github.com/canonical/chrony-operator/actions/workflows/promote_charm.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

A [Juju](https://juju.is/) [charm](https://documentation.ubuntu.com/juju/3.6/reference/charm/)
for deploying and managing the [Chrony](https://chrony-project.org) NTP server 
in your systems.

This charm simplifies the configuration and maintenance of `chrony` across a 
range of environments, enabling basic time provision and synchronization with 
NTP servers.

## Get started
In this section, we will deploy the Chrony charm, which can be used as a time source for NTP clients.  
You’ll need a workstation, e.g., a laptop, with sufficient resources to launch a virtual machine with 4 CPUs, 8 GB RAM, and 50 GB disk space.

### Set up
You can follow the tutorial [here](https://documentation.ubuntu.com/juju/3.6/howto/manage-your-juju-deployment/set-up-your-juju-deployment-local-testing-and-development/) to set up a test environment for Juju with LXD.

### Deploy
From inside the virtual machine, deploy the Chrony charm using the `juju deploy` command.

```
juju deploy chrony --channel latest/edge
```

### Basic operations
When the Chrony charm has finished deployment and installation, it should show the message `no time source configured`.  
Now we can run the `juju config` command to configure an upstream time source for the Chrony charm. In this example, we will use Ubuntu's time server.

```
juju config chrony sources=ntp://ntp.ubuntu.com
```

Shortly after the configuration, the Chrony charm should transition into the active state and be able to provide time to other NTP clients.

## Learn more
* [Read more](https://charmhub.io/chrony)
* [Official webpage](https://chrony-project.org)
* [Troubleshooting](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)

## Project and community
* [Issues](https://github.com/canonical/chrony-operator/issues)
* [Contributing](https://charmhub.io/chrony/docs/how-to-contribute)
* [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
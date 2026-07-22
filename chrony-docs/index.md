# Chrony charm

A [Juju](https://juju.is/) [charm](https://documentation.ubuntu.com/juju/3.6/reference/charm/)
for deploying and managing the [Chrony](https://chrony-project.org) NTP server
in your systems.

This charm simplifies the configuration and maintenance of Chrony across a
range of environments, enabling basic time provision and synchronization with
NTP servers.

Like any Juju charm, this charm supports one-line deployment, configuration, integration, scaling, and more. 
For Chrony, this includes: 
* Time source management
* NTS (Network Time Security) and NTS certificate management
* Enhanced observability and monitoring

The Chrony charm allows for deployment on many different virtualization platforms, from [LXD](https://canonical.com/lxd) to 
[OpenStack](https://ubuntu.com/openstack) to public cloud offerings.

This charm will make operating Chrony  simple and straightforward for DevOps or SRE teams through Juju's clean interface. 

## In this documentation

|                                                                                                                                           |                                                                                                                              |
|-------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| [Tutorials](https://charmhub.io/chrony/docs/Tutorials)</br>  Get started - a hands-on introduction to using the charm for new users </br> | [How-to guides](https://charmhub.io/chrony/docs/How%20To) </br> Step-by-step guides covering key operations and common tasks |
| [Reference](https://charmhub.io/chrony/docs/Reference) </br> Technical information - specifications, APIs, architecture                                           | [Explanation](https://charmhub.io/chrony/docs/Explanation) </br> Concepts - discussion and clarification of key topics                               |

## Contributing to this documentation

Documentation is an important part of this project, and we take the same open-source approach to the documentation as 
the code. As such, we welcome community contributions, suggestions and constructive feedback on our documentation. 
Our documentation is hosted on the [Charmhub forum](https://discourse.charmhub.io/) 
to enable easy collaboration. Please use the "Help us improve this documentation" links on each documentation page to 
either directly change something you see that's wrong, ask a question or make a suggestion about a potential change via 
the comments section.

If there's a particular area of documentation that you'd like to see that's missing, please 
[file a bug](https://github.com/canonical/chrony-operator/issues).

## Project and community

The Chrony Operator is a member of the Ubuntu family. It's an open-source project that warmly welcomes community 
projects, contributions, suggestions, fixes, and constructive feedback.

- [Code of conduct](https://ubuntu.com/community/code-of-conduct)
- [Get support](https://discourse.charmhub.io/)
- [Join our online chat](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
- [Contribute](https://github.com/canonical/chrony-operator/blob/main/CONTRIBUTING.md)

Thinking about using the Chrony Operator for your next project? 
[Get in touch](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)!

# Contents

1. [Tutorial](tutorial)
1. [How-to](how-to)
  1. [Upgrade](how-to/upgrade.md)
1. [Reference](reference)
  1. [Charm architecture](reference/charm-architecture.md)
1. [Explanation](explanation)

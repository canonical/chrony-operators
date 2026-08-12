# Chrony client operator

A [Juju](https://juju.is/) [subordinate charm](https://documentation.ubuntu.com/juju/latest/reference/charm/#subordinate)
install and managing Chrony as a NTP client. 

Like any Juju charm, it supports one-line deployment, configuration,
integration, scaling, and more. Specifically, the Chrony client charm
can:

* Install Chrony as an NTP client
* Configure time sources
* Integrate with COS for time tracking status observability

The Chrony client charm allows for deployment on many different machine
platforms, from [MAAS](https://maas.io/) to [Charmed OpenStack](https://ubuntu.com/openstack)
to public cloud offerings.

This charm will make managing Chrony as NTP client simple and 
straightforward for DevOps or SRE teams through Juju's clean interface. 

## In this documentation

|                                                                                                               |                                                                                              |
|---------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| [Tutorials](./tutorial.md)</br>  Get started - a hands-on introduction to using the charm for new users </br> | [How-to guides](./how-to) </br> Step-by-step guides covering key operations and common tasks |
| [Reference](./reference) </br> Technical information - specifications, APIs, architecture                     | [Explanation](./explanation) </br> Concepts - discussion and clarification of key topics     |

## Contributing to this documentation

Documentation is an important part of this project, and we take the same open-source approach
to the documentation as the code. As such, we welcome community contributions, suggestions, and
constructive feedback on our documentation.
See [How to contribute](./how-to/contribute.md) for more information.


If there's a particular area of documentation that you'd like to see that's missing, please 
[file a bug](https://github.com/canonical/chrony-client-operator/issues).

## Project and community

The Chrony client charm is a member of the Ubuntu family. It's an open-source project that warmly welcomes community 
projects, contributions, suggestions, fixes, and constructive feedback.

- [Code of conduct](https://ubuntu.com/community/code-of-conduct)
- [Get support](https://discourse.charmhub.io/)
- [Join our online chat](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
- [Contribute](https://github.com/canonical/chrony-client-operator/blob/main/CONTRIBUTING.md)

Thinking about using the Chrony client charm for your next project? 
[Get in touch](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)!

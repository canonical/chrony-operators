
# Chrony

[Chrony](https://chrony-project.org) is an implementation of the Network Time
Protocol (NTP).

## Chrony charms

This documentation covers two charms:

* The [Chrony charm](https://charmhub.io/chrony) deploys and manages Chrony as
  an NTP server. It supports time source management, Network Time Security
  (NTS) and certificate management, and observability and monitoring.
* The [Chrony client charm](https://charmhub.io/chrony-client) is a
  [subordinate charm](https://documentation.ubuntu.com/juju/latest/reference/charm/#subordinate)
  that installs and manages Chrony as an NTP client. It configures time
  sources and integrates with Canonical Observability Stack (COS) for time
  tracking status observability.

Like any Juju charm, both charms support one-line deployment, configuration,
integration, scaling, and more. Together, they make operating Chrony simple
and straightforward for DevOps and SRE teams through Juju's clean interface.


## In this documentation

|                                                                                                               |                                                                                              |
|---------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| [Tutorials](tutorial)</br>  Get started - a hands-on introduction to using the charms for new users </br> | [How-to guides](how-to) </br> Step-by-step guides covering key operations and common tasks |
| [Reference](reference) </br> Technical information - specifications, APIs, architecture                     | [Explanation](explanation) </br> Concepts - discussion and clarification of key topics     |

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
1. [Reference](reference)
1. [Explanation](explanation)

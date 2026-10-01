# Security overview

<!-- vale Canonical.011-Headings-not-followed-by-heading = NO -->

## Risks

The Chrony client charm is a simple charm with a minimal attack surface.
The Chrony service is configured as a pure NTP client, and the Chrony
client charm does not expose any ports. The Chrony exporter only listens
on `localhost`.

## Security patches

`chrony` is installed from the Ubuntu archive, and security patches are
delivered through Ubuntu archive updates. Use Ubuntu Pro for faster
security responses. See [the Ubuntu Pro charm](https://charmhub.io/ubuntu-advantage).

`chrony_exporter` is installed from the Platform Engineering team’s
PPA (`ppa:canonical-is-devops/chrony-charm`) and maintained by the
Platform Engineering team.

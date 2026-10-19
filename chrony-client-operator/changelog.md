# Changelog

## 2026-10-19

* Added Juju 4 integration tests on amd64.
* Moved the uninstall cleanup from the `remove` hook to the `stop` hook,
  as Juju 4 does not run the `remove` hook for removed subordinate units.

## 2026-10-05

* Added support for the Ubuntu 26.04 LTS base and the arm64, s390x and
  ppc64el architectures.
* Allowed the chrony_exporter AppArmor profile to memory-map its own
  binary, fixing the exporter crashing inside LXD containers.
* Installed a systemd drop-in so chrony runs inside containers on
  Ubuntu 26.04 LTS, where the packaged service skips containers.

## 2026-05-19

* Increased the `ChronyTrackingStaleMeasurement` alert threshold from
  30 minutes to 8 hours to reduce false positives.

## 2026-01-22

* Bundle chrony_exporter inside the charm instead of installing it from
  a PPA.

## 2025-12-17

* Moved charm-architecture.md from Explanation to Reference category.

## 2014-05-31

### Added

* Created the initial version of the Chrony client charm, a subordinate
  charm that configures Chrony as an NTP client on the target machine.
* Added the initial set of charm documentation.


# Changelog

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


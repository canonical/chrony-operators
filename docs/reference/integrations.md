# Integrations

<!-- vale Canonical.011-Headings-not-followed-by-heading = NO -->

### `cos-agent`

_Interface_: `cos_agent`    
_Supported charms_: [Grafana agent](https://charmhub.io/grafana-agent)

Chrony client charm uses the `cos-agent` relation to provide COS-related
information, such as Prometheus metrics, Grafana dashboards, and
Prometheus alerts, to the Grafana agent.

Example `cos-agent` integrate command:

```
juju integrate chrony-client:cos-agent grafana-agent
```

### `juju-info`

_Interface_: `juju-info`    
_Supported charms_: every charm

The `juju-info` interface is a special and implicit relationship that
works with any charm. It is mainly useful for subordinate charms
, in this case Chrony client charm, that can add functionality to any
existing machine without the host charm being aware of it.

Example `juju-info` integrate command:

```
juju integrate chrony-client:juju-info ubuntu
```

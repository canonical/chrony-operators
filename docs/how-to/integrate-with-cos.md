<!-- vale Canonical.007-Headings-sentence-case = NO -->
# How to integrate with COS
<!-- vale Canonical.007-Headings-sentence-case = YES -->

## Prerequisites

The COS integration for the Chrony client charm is provided by
the [Grafana Agent charm](https://charmhub.io/grafana-agent). Before
integrating the COS charms, you must first integrate the Chrony client
charm with the Grafana Agent charm. Because the Grafana Agent charm is
also a subordinate charm, you cannot directly integrate it to the Chrony
client charm. Instead, integrate the Grafana Agent charm with a
principal charm first, then integrate it to the Chrony client charm.

Assuming you have already integrated the Chrony client charm with the
Ubuntu charm as the principal charm:

```bash
juju deploy chrony-client
juju integrate chrony-client:juju-info ubuntu
```

Use the Grafana Agent charm’s `juju-info` interface to integrate it to the
principal charm:

```bash
juju relate grafana-agent:juju-info ubuntu
```

Then integrate the Chrony client charm to the Grafana Agent charm.

<!-- vale Canonical.007-Headings-sentence-case = NO -->
## Integrate with the Prometheus K8s operator
<!-- vale Canonical.007-Headings-sentence-case = YES -->

Deploy and integrate
the [`prometheus-k8s`](https://charmhub.io/prometheus-k8s) charm with the
Grafana Agent charm through the `send-remote-write` relation using the
`prometheus_remote_write` interface. The Grafana Agent will push the
Prometheus metrics collected from the Chrony exporter to the Prometheus
charm.

Because the Prometheus charm is a Kubernetes charm, you must establish a
cross-model relation. For more information on cross-model relations and
how to add one, see [the cross-model relation documentation](https://documentation.ubuntu.com/juju/latest/reference/relation/#cross-model).

```bash
juju consume cos-juju-controller:cos-juju-user/cos-model.receive-remote-write
juju integrate grafana-agent:send-remote-write receive-remote-write
```

<!-- vale Canonical.007-Headings-sentence-case = NO -->
## Integrate with the Grafana K8s operator
<!-- vale Canonical.007-Headings-sentence-case = YES -->

Deploy and integrate the [`grafana-k8s`](https://charmhub.io/grafana-k8s)
charm with the Grafana Agent charm through the
`grafana-dashboards-provider` relation using the `grafana_dashboard`
interface. The Grafana Agent will relay the dashboards provided by the
Chrony client charm to the Grafana charm.

As with the Prometheus charm, the Grafana charm is a Kubernetes charm,
so you must establish a cross-model relation. For details,
see [the cross-model relation documentation](https://documentation.ubuntu.com/juju/latest/reference/relation/#cross-model).

```bash
juju consume cos-juju-controller:cos-juju-user/cos-model.grafana-dashboard
juju integrate grafana-agent:grafana-dashboards-provider grafana-dashboard
```

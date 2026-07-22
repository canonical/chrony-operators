<!-- vale Canonical.007-Headings-sentence-case = NO -->
# Deploy the Chrony client charm
<!-- vale Canonical.007-Headings-sentence-case = YES -->

The Chrony client charm installs and configures Chrony as the NTP client
on target systems. It also provides observability into the target
system’s time-tracking status. This tutorial will walk you through each
step of deploying the Chrony client charm.

## What you'll need

<!-- vale Canonical.013-Spell-out-numbers-below-10 = NO -->
- A working station, e.g., a laptop, with AMD64 architecture.
- Juju 3 installed and bootstrapped to a LXD controller. You can
  accomplish this process by using a Multipass VM as outlined in this
  guide: [Set up your test environment](https://canonical-juju.readthedocs-hosted.com/en/latest/user/howto/manage-your-deployment/manage-your-deployment-environment/#set-things-up)
<!-- vale Canonical.013-Spell-out-numbers-below-10 = YES -->

## What you'll do

- Deploy the [Ubuntu charm](https://charmhub.io/ubuntu)
- [Deploy and Chrony client charm on the Ubuntu charm](#deploy-the-chrony-client-charm-on-the-ubuntu-charm)
- [Configure time sources]

## Set up the environment

To be able to work inside the Multipass VM first you need to log in with
the following command:

```bash
multipass shell my-juju-vm
```

[note]
If you're working locally, you don't need to do this step.
[/note]

To manage resources effectively and to separate this tutorial's workload
from your usual work, create a new model in the MicroK8s controller
using the following command:

```bash
juju add-model chrony-client-tutorial
```

<!-- vale Canonical.007-Headings-sentence-case = NO -->
## Deploy Ubuntu charm
<!-- vale Canonical.007-Headings-sentence-case = YES -->

As the Chrony client charm is
a [subordinate charm](https://documentation.ubuntu.com/juju/latest/reference/charm/#subordinate),
it requires a principal charm to be deployed on. The Chrony client charm
can be deployed with any charm. In this tutorial, we will choose
the [Ubuntu charm](https://charmhub.io/ubuntu).

```bash
juju deploy ubuntu --base ubuntu@24.04
```

<!-- vale Canonical.007-Headings-sentence-case = NO -->
## Deploy the Chrony client charm
<!-- vale Canonical.007-Headings-sentence-case = YES -->

The following commands deploy the Chrony client charm and integrate it
with the Ubuntu charm to create a principal-subordinate relation.

```bash
juju deploy chrony-client --channel latest/edge --base ubuntu@24.04
juju integrate chrony-client:juju-info ubuntu
```

Run `juju status` to see the current status of the deployment. The
output should be similar to the following:

```
Model                   Controller  Cloud/Region         Version  SLA          Timestamp
chrony-client-tutorial  lxd         localhost/localhost  3.6.2    unsupported  13:45:19+08:00

App            Version  Status  Scale  Charm          Channel        Rev  Exposed  Message
chrony-client           active      1  chrony-client                   1  no       
ubuntu         24.04    active      1  ubuntu         latest/stable   26  no       

Unit                Workload  Agent  Machine  Public address  Ports  Message
ubuntu/0*           active    idle   0        10.212.71.96           
  chrony-client/0*  active    idle            10.212.71.96           

Machine  State    Address       Inst id        Base          AZ  Message
0        started  10.212.71.96  juju-2cbd10-0  ubuntu@24.04      Running
```

The deployment finishes when the status shows "active" for both the
Ubuntu and Chrony client charms.

## Configure time sources

By default, the Chrony client charm uses Ubuntu’s NTP servers 
(ntp.ubuntu.com) as its time source. You can configure the charm to use
different time sources, for example, switching to the NTP Pool servers,
by running the following command:

```bash
juju config chrony-client sources='ntp://0.pool.ntp.org?iburst=true&maxsources=4,
ntp://1.pool.ntp.org?iburst=true&maxsources=4,
ntp://2.pool.ntp.org?iburst=true&maxsources=4,
ntp://3.pool.ntp.org?iburst=true&maxsources=4'
```

The charm should reach the active state when the configuration is 
successful. It will end up in the blocked state if the configuration 
value is invalid.

## Clean up the environment

Congratulations! You have successfully deployed the Chrony client charm.

You can clean up your environment by following this guide:
[Tear down your test environment](https://canonical-juju.readthedocs-hosted.com/en/3.6/user/howto/manage-your-deployment/manage-your-deployment-environment/#tear-things-down)

# How to set up time sources

Chrony alone cannot provide time; it requires another time source, either a 
reference clock or another NTP server, to supply time to Chrony itself. 
Currently, the Chrony charm only supports using another NTP server as the 
time source.

<!-- vale Canonical.007-Headings-sentence-case = NO -->
## Use another NTP server
<!-- vale Canonical.007-Headings-sentence-case = YES -->

Provide the IP address or domain name of the NTP server to be used as the time 
source in URL format, for example, `ntp://ntp.example.com`, and pass this URL to
the Chrony charm using the `sources` charm configuration. 
The domain in the URL will be treated as a pool address for the NTP server.

You can adjust the time source using 
[pool options listed in the Chrony configuration](https://chrony-project.org/doc/4.6.1/chrony.conf.html). 
These options are passed to the Chrony charm as URL parameters. 
For example, to enable `iburst` and set `maxsources` to 2, use the 
URL `ntp://ntp.example.com?iburst=true&maxsources=2`. 
The only exception option is NTS, as explained in the next section.

<!-- vale Canonical.007-Headings-sentence-case = NO -->
## Use another NTS server with NTS enabled
<!-- vale Canonical.007-Headings-sentence-case = YES -->

To use another NTS server with NTS enabled for the time source, follow a 
similar process as using an NTP server but change the protocol to `nts`.
For example, use `nts://ntp.example.com`. 
All pool options available for a plain NTP time source are also 
applicable to an NTS time source.
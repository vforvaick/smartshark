# MVP Troubleshooting Playbooks

Smartshark MVP playbooks should produce tool-grounded claims with evidence links.

## Generic Network Playbooks

1. **TCP Health** — retransmission, duplicate ACK, reset, zero window, and handshake failure.
2. **DNS Resolution** — no response, NXDOMAIN/SERVFAIL, high latency, and mismatched server.
3. **HTTP/API Latency & Errors** — status 4xx/5xx, slow server response, connection reuse, and resets.
4. **TLS Handshake** — alerts, version/cipher mismatch, and visible handshake failure symptoms.
5. **Path / Visibility Sanity** — one-way traffic, asymmetric capture, missing SYN/SYN-ACK, and SPAN blind spots.

## Analysis Profiles

The default profile is **General Network Troubleshooting**. MVP profile selection is a single primary profile per capture artifact. Optional profiles should tune the same generic playbooks with environment-specific interpretation rules instead of splitting the product into separate modules.

- **General Network Troubleshooting** — default profile; runs the generic network playbooks with no vendor assumptions.
- **F5 Load Balancer** — tunes TCP Health and Path / Visibility Sanity to distinguish client-side versus server-side connections, health checks, pool-member behavior, SNAT, F5-generated resets, and capture vantage point ambiguity.
- **Infoblox DNS** — tunes DNS Resolution with Infoblox appliance context, DNS service response/no-response evidence, response codes, latency, and endpoint capture comparison.
- **Verifone intelliNAC** — tunes TCP, HTTP/API, TLS, and Path / Visibility checks around terminal connectivity, authorization/authentication flow, network reachability, and app/protocol failure evidence.

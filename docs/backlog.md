# Backlog

## Post-MVP Decryption

- **TLS key log / decrypted capture support** — allow analysts to provide decryption material or pre-decrypted captures so application-layer evidence can be verified when policy permits.

## Post-MVP Capture Modes

- **Live traffic capture / streaming analysis** — analyze traffic while it is being captured, after the offline capture-file workflow is proven.

## Post-MVP Collaboration

- **Viewer role** — read-only local/project role for viewing shared captures and reports without upload, analysis, or delete permissions.
- **Team workspaces and RBAC** — shared capture libraries, multi-user comments, permissions, and durable share links after the evidence model is proven in simple local Admin/Analyst mode.

## Post-MVP Data Integrations

- **Infoblox Grid/API/log integration** — correlate packet evidence with DNS/DHCP service logs, zone/recursive role context, leases, and appliance events after PCAP-only analysis is proven.

## Post-MVP Evidence Link Targets

These are intentionally not part of the first MVP, but should remain visible for future planning.

- **Live device CLI link** — jump from analysis/evidence to a bounded device command/session when troubleshooting requires device-side validation.
- **Ticketing system link** — connect evidence and analysis to an incident/ticket record.
- **External topology link** — open related network topology or dependency context outside Smartshark.
- **SIEM / observability link** — pivot from packet evidence to related alerts, logs, or telemetry in external platforms.

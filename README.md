# Smartshark

Smartshark is an evidence-first network troubleshooting workspace that combines Wireshark-style packet analysis with bounded AI investigations and clickable evidence links.

## Current MVP shape

- Python/FastAPI backend under `src/backend`.
- React/Next.js frontend under `src/frontend`.
- Local-first storage and auth foundations.
- Evidence Map, Evidence Link, Analysis Run, Analysis Profile, Redaction Policy, report, capture lifecycle, and packet workspace foundations.

## Verify locally

```bash
src/backend/.venv/bin/python -m pytest -q
cd src/frontend && npm run lint && npm run build
```

## Documentation

Start with [`docs/README.md`](./docs/README.md) and [`CONTEXT.md`](./CONTEXT.md).

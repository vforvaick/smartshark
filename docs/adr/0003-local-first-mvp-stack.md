# Local-First MVP Stack

Smartshark MVP will use a Python/FastAPI backend with a separate worker process, SQLite for local single-instance storage, React/Next.js for the investigation workspace, and Wireshark tooling through the Packet Query Engine. This stack prioritizes local/self-hosted packet-processing reliability, subprocess orchestration, and fast product iteration while leaving room to move storage to Postgres and AI providers to local or hosted models later.

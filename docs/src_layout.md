# Source (`src/`) layout — enterprise scaffold

This document describes the enterprise-style directory structure created under `src/` and the conventions used by this project. It is intended for contributors and AI coding agents to become productive quickly.

Overview
- `src/` is organized as Python packages (each directory contains an `__init__.py` placeholder).
- Purpose: separate concerns (agents, orchestration, services, models, tool-calls, UI, data, tests, config, utils, logging, examples).

Top-level packages (examples and key files)
- `src/agents/` — agent classes. Example: `src/agents/example_agent.py` (implements `handle_request(context)`).
- `src/core/` — orchestration primitives and entrypoints.
- `src/services/` — adapters to external systems (mocked adapters live here).
- `src/models/` — domain dataclasses and models (ChangeRecord, ApprovalRecord, AuditEvent).
- `src/tools/` — tool-call implementations (async functions registered with agents). Common tool names: `lookup_data`, `check_authorization`, `send_notification`, `generate_report`.
- `src/ui/` — UI pages (Streamlit/Flask) that surface mocked notifications and audit views.
- `src/data/` — CSV-backed data used by tool calls (see `/docs/csv_schemas.md`). Added `src/data/README.md` for guidance.
- `src/config/` — configuration helpers and `.env.example` (see `src/config/.env.example`).
- `src/tests/` — unit & integration tests (use `python -m unittest discover`).
- `src/utils/`, `src/logging/`, `src/examples/` — helpers, audit logging, and usage examples.

Conventions and patterns (discoverable, not aspirational)
- Agents are local Python classes with a `handle_request(context)` method and call Azure-hosted models using credentials from `.env`.
- Tool calls are implemented as Python async functions in `src/tools/` and must log to the audit trail (`src/logging/`). They operate over CSV files in `src/data/` and are not REST endpoints.
- Configuration values are read from `src/config/.env.example` (copy to `src/.env` for local development). Key env vars: `AGENT_MODEL_DEPLOYMENT_NAME`, `PROJECT_ENDPOINT`, `AGENT_TEMPERATURE`.
- Tests are discovered with the standard unittest discovery: `python -m unittest discover`.

Small contract for contributors / agents
- Inputs: agent `context` dict, CSV data stored under `src/data/`, env vars from `src/.env`.
- Outputs: agent decision objects, audit events written to the audit trail, and optionally generated reports (report ids/summaries).
- Error modes: missing CSV files, schema mismatch (see `/docs/csv_schemas.md`), missing env vars, or Azure model call failures.

Edge cases to watch (from current layout)
- Empty or missing CSVs — tool calls should return sensible empty results and log schema validation errors.
- Missing `AGENT_MODEL_DEPLOYMENT_NAME` — agents must detect and surface a clear error message.
- Long-running tool calls — tool calls are async; calling agents should handle timeouts and log partial progress.

References
- Onboarding & architecture: `/docs/application.md`, `/docs/architecture.md`.
- CSV schemas: `/docs/csv_schemas.md` (define canonical formats for `src/data/`).
- Example agent: `src/agents/example_agent.py`.
- Env example: `src/config/.env.example`.

If anything here is unclear or you'd like more detail (example orchestrator, tool-call stubs, or tests), tell me which area to expand.

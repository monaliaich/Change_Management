# Copilot & AI Agent Instructions for Change Management

## Project Overview
This is a Multi-Agent Change Management Control Demo. The system is built around local Python agents that orchestrate IT change validation workflows, using the Azure AI SDK for reasoning and tool calls. All orchestration is local (no REST API); agent-to-agent and agent-to-user communication is mocked and surfaced via UI pages.

## Key Architectural Patterns
- **Agents**: Implemented as Python classes in `src/`, each with a `handle_request(context)` method. Agents use Azure-hosted models for reasoning, credentials from `.env`, and register tool calls as Python async functions.
- **Tool Calls**: All agent tool calls (e.g., `lookup_data`, `check_authorization`, `send_notification`, `generate_report`) are Python async functions, not REST endpoints. See `/docs/architecture.md` and `/docs/toolcalls.md` for details.
- **Data**: All data is stored in CSV files (see `/docs/csv_schemas.md`). Data access is via tool calls, not direct file reads in agent logic.
- **Environment**: Use `python-dotenv` to load environment variables from `/src/.env`. Never commit secrets; update `.env.example` when adding variables.
- **UI**: All notifications and agent-to-user/manager communication are mocked and surfaced as UI pages (not real emails).

## Developer Workflow
- Install Python 3.10+ and dependencies from `requirements.txt`.
- Copy `/src/.env.example` to `/src/.env` and fill in required values.
- Run the main orchestrator (see `/docs/application.md`). No separate MCP server is required.
- Use feature branches for all changes; open PRs for merges to `main`.
- Validate all CSV data against schemas in `/docs/csv_schemas.md`.
- Use `python -m unittest discover` for tests. Test files/classes must be named accordingly.

## Project-Specific Conventions
- All agent logic is local Python, not REST or microservices.
- Tool calls are always async Python functions, registered with the agent.
- All workflow/audit events are logged for traceability.
- User/manager responses are always mocked, not real-time.
- Follow the canonical workflow in `/docs/flow.md` and UI in `/docs/wireframe.md`.

## Key References
- `/docs/application.md`: Onboarding, environment, workflow, agent pattern
- `/docs/architecture.md`: System architecture, tool call mapping, agent responsibilities
- `/docs/flow.md`: Canonical workflow
- `/docs/toolcalls.md`: Tool call protocol
- `/docs/csv_schemas.md`: Data schemas
- `/docs/Contributing.md`: Developer onboarding, coding standards

## Example: Agent Implementation
```python
class InvestigationAgent:
    def handle_request(self, context):
        # Use Azure SDK, credentials from .env
        # Register tool calls as async functions
        ...
```

## When in Doubt
- Start with `/docs/application.md` and `/docs/architecture.md`.
- Ask clarifying questions in PRs or issues.
- Update documentation with every significant change.

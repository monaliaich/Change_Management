# Change Management

# See Also
- [application.md](application.md): End-to-end workflow, agent responsibilities, status codes, CSV schemas, audit/logging, deployment & testing guidance
- [architecture.md](architecture.md): System architecture, Agent2Agent protocol, MCP server, sequence diagrams, toolcall mappings, module responsibilities
- [flow.md](flow.md): Canonical workflow diagram
- [toolcalls.md](toolcalls.md): MCP tool call protocol and agent tool call details
- [csv_schemas.md](csv_schemas.md): Canonical CSV schemas and data model
- [README.md](README.md): Documentation index and onboarding

## Developer Onboarding & Contribution Guide

Welcome to the Multi-Agent Change Management Control Demo project! This guide will help you get started as a contributor and ensure smooth collaboration.

**Agent Implementation Pattern:**
All agents must be implemented as local Python classes with a `handle_request(context)` method that calls an Azure-hosted model for reasoning/decision-making, using the Azure AI SDK and credentials from `.env`. See `src/AdvisoryAgent.py` and `/examples/agent_usage_example.py` for reference.

**Example usage:**
See `/examples/agent_usage_example.py` for a minimal example of agent instantiation and usage.


### 1. Project Setup
- Clone the repository and review the `/docs/` for architecture, approach, and setup.
- Install Python 3.10+ and all dependencies listed in `requirements.txt`.
- Copy `/src/.env.example` to `/src/.env` and fill in required environment variables (see `/docs/application.md`).
- Never commit real `.env` files or secrets to version control. Always update `.env.example` when adding new variables.
- Use `python-dotenv` to load environment variables in all entrypoints, and reference them in code using `os.getenv()`.
- Ensure all CSV data files are present in `/data/` and match the documented schema in `/docs/csv_schemas.md`.

### 2. Development Workflow
- Use feature branches for all new features, bug fixes, or experiments.
- Name branches descriptively (e.g., `feature/agent2agent-protocol`).
- Open pull requests for all merges into `master` or main branches.
- Require code review and successful tests before merging.
- Update documentation and checklists with every significant change.


### 3. Coding Standards
- Follow the architecture and interface guidelines in `/docs/architecture.md` and `/docs/application.md`.
- All agents must implement a `handle_request(context)` method and follow the local class + Azure model pattern (see `/docs/architecture.md`).
- Use clear, descriptive variable and function names.
- Add docstrings and comments for all public classes and functions.
- Write unit and integration tests for all new code.


### 4. Testing & Validation
- Use the provided sample data and test scenarios in `/docs/application.md` and `/data/`.
- Mock all user/manager responses and tool calls as described in `/docs/application.md`.
- Validate audit trail and status transitions for all workflows.


### 5. Communication & Collaboration
- Ask clarifying questions early and often.
- Document all assumptions in code comments, pull requests, or the changelog.
- Use the project chat or issue tracker for open questions.
- Review and update assumptions as new information becomes available.
- Always review and update documentation as part of every pull request or feature branch.

### 6. Documentation
- Update relevant documentation files with every significant code or workflow change.
- Assign responsibility for documentation updates as part of each pull request or feature branch.
- Review documentation as part of code review and before merging.

### 7. Changelog & Dev Diary
- Summarize major changes and decisions in `CHANGELOG.md` or a dev diary.
- Use clear commit messages to indicate documentation and code changes.

## Troubleshooting Tips
- If Azure model calls fail, check your `.env` file for correct credentials and deployment names.
- If tests are not discovered, ensure your test files and classes follow the `test_*.py` and `Test*` naming conventions, and run tests using `python -m unittest discover` from the project root.
- For agent usage, see `/examples/agent_usage_example.py` for working patterns.
- For more details on the agent pattern, see `/docs/architecture.md` and `/docs/application.md`.


Thank you for contributing! Your work helps ensure the project is robust, auditable, and demo-ready.

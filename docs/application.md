# See Also
- [architecture.md](architecture.md): System architecture, Agent2Agent protocol, MCP server, sequence diagrams, toolcall mappings, module responsibilities
- [flow.md](flow.md): Canonical workflow diagram
- [wireframe.md](wireframe.md): UI wireframes and layouts
- [toolcalls.md](toolcalls.md): MCP tool call protocol and agent tool call details
- [csv_schemas.md](csv_schemas.md): Canonical CSV schemas and data model
- [CONTRIBUTING.md](CONTRIBUTING.md): Developer onboarding and contribution process
- [README.md](README.md): Documentation index and onboarding

# Quickstart & Onboarding

To get started with the Multi-Agent Access Control Demo:

For a high-level workflow overview, see `/docs/flow.md`. For UI wireframes and layouts, see `/docs/wireframe.md`. These files provide canonical sources for the process flow and user interface design.

1. **Clone the repository** and review the `/docs/` directory for architecture, approach, and setup.
2. **Install Python 3.10+** and all dependencies listed in `requirements.txt`.
3. **Copy `/src/.env.example` to `/src/.env`** and fill in all required environment variables (see below).
4. **Never commit real `.env` files or secrets to version control.** Always use `.env.example` for onboarding and update it whenever a new variable is added.
5. **Use `python-dotenv` to load environment variables** in all entrypoints, and reference them in code using `os.getenv()`.
6. **Ensure all CSV data files are present** in `/data/` and match the documented schema.
7. **Run the main orchestrator** as described below. (No separate MCP server is required; all orchestration is local using the Azure SDK. The "MCP server" is now a local Python orchestration pattern, not a REST API. All notifications and agent-to-user/manager communication are mocked and surfaced as UI pages.)

For more details on agent implementation, see the "Agent Implementation Pattern" section below and `/docs/architecture.md`.

For canonical workflow diagrams, see `/docs/flow.md`. For UI wireframes and layouts, see `/docs/wireframe.md`.

---

## Environment Variables

The following environment variables must be set in `/src/.env` for the system to function:

| Variable                        | Description                                                      |
|----------------------------------|------------------------------------------------------------------|
| AGENT_MODEL_DEPLOYMENT_NAME      | Name of the Azure OpenAI deployment for agents                   |
| PROJECT_ENDPOINT                 | Base URL for the Azure AI Project or MCP server                  |
| AZURE_SUBSCRIPTION_ID            | Azure subscription ID for resource access                        |
| AZURE_RESOURCE_GROUP_NAME        | Azure resource group name                                        |
| MCP_SERVER_URL                   | (Legacy) URL for the local MCP server (not used in Azure SDK-based pattern)    |
| AGENT_TEMPERATURE (optional)     | Temperature for agent model calls (float, default: 0.2)          |

**Setup:**
1. Copy `/src/.env.example` to `/src/.env` and fill in the required values.
2. Never commit real `.env` files or secrets to version control.
3. Update `.env.example` whenever a new variable is added.

**Troubleshooting:**
- If you encounter schema validation errors when reading or writing CSVs, check that your data files match the schemas in `/docs/csv_schemas.md`.
If you encounter errors with Azure model calls, verify your `.env` file and Azure resource access.
If agent tests are not running, ensure your test files and classes are named correctly and use `python -m unittest discover`.
For agent usage patterns, see `/examples/agent_usage_example.py`.
For the canonical agent pattern, see `/docs/architecture.md` and `/docs/application.md`.
# Onboarding: Implementing and Extending Agents

To implement or extend an agent:

1. Create a new Python class (e.g., `InvestigationAgent`) in `/src/`.
2. Implement a `handle_request(context)` method.
3. In `handle_request`, use the Azure AI SDK (see example in `architecture.md`) to call the appropriate Azure-hosted model, using credentials from `.env`.
4. Register all tool calls (data lookup, authorization, notification, report generation) as Python async functions with the agent using the Azure SDK. Do not use REST endpoints for tool calls; all tool calls are Python async functions registered with the agent.
5. Do not register or persist agents in Azure; all orchestration is local.
6. Use the structure and best practices from `src/old/agent_example.py` as a template for model calls and tool integration.
6. Add or update docstrings to clarify the agent's pattern and responsibilities.
7. Add tests and example usage for your agent.

This ensures all agents follow the correct pattern and are easy to maintain and extend.

# Agent Implementation, Protocol, Workflow, and Audit Trail

For full details on agent implementation pattern, Agent2Agent protocol, workflow steps, audit/logging, and CSV schema definitions, see `/docs/architecture.md`.

This document focuses on onboarding, environment setup, deployment, troubleshooting, and contributor guidance. For technical architecture, agent responsibilities, and workflow mapping, refer to the architecture documentation.

# Application Documentation

## Project Review & Progress Tracking
## Code Review & Pair Programming Policy
## Continuous Documentation Updates
## Sample Data & Test Scenarios
## End-to-End Demo Flow Prioritization
## Contributor Guidance: Clarifying Questions & Assumptions
## Version Control Branching & Merging Policy
## Acceptance Criteria & User Story Refinement
## Keeping the AI Coding Assistant Up to Date

To maximize the effectiveness of the AI coding assistant:
- Regularly update documentation and checklists with new requirements, architecture changes, and lessons learned
- Summarize major changes and decisions in the changelog or dev diary
- Ensure the AI assistant is provided with the latest context, including updated `/docs/`, `/src/`, and `/data/` files
- Review and refresh the assistant’s context window at the start of each major development phase

This practice ensures the assistant remains a valuable, context-aware contributor throughout the project.

Acceptance criteria and user stories will be:
- Reviewed at the start of each sprint or milestone
- Updated as requirements evolve or new insights are gained
- Used as the basis for UI acceptance and demo validation
- Documented in `/docs/application.md` and referenced in `/docs/TODO.md`

This ensures the project remains aligned with user needs and stakeholder expectations.

To maintain code quality and enable safe collaboration:
- Use feature branches for all major features, bug fixes, or experiments
- Name branches descriptively (e.g., `feature/agent2agent-protocol`)
- Open pull requests for all merges into `master` or main branches
- Require code review and successful tests before merging
- Resolve conflicts and document merge decisions in the changelog

This policy ensures a clean, auditable project history and reduces integration risks.

Contributors are encouraged to:
- Ask clarifying questions early and often, especially when requirements or workflows are unclear
- Document all assumptions in code comments, pull requests, or the changelog
- Use the project chat or issue tracker for open questions
- Review and update assumptions as new information becomes available

This practice reduces misunderstandings and helps maintain project clarity.

The team will prioritize building complete, working end-to-end demo flows before focusing on optimization or refactoring. This approach ensures:
- Early validation of the full system
- Rapid feedback on integration points
- Clear demonstration value for stakeholders

Optimization and refactoring will be scheduled only after the main demo flows are functional and tested.

Sample data is provided in the `/data/` directory:
- `users.csv`, `hr_mutations.csv`, `authorisations.csv`, `role_authorisations.csv`, `roles.csv`, `sickLeave.csv`, `vacation.csv`, `audit_trail.csv`

Test scenarios should be created early and used to validate agent workflows and UI pages. Example scenarios:
- HR mutation with valid/invalid rights
- Sick leave or vacation claim validation
- Manager approval/denial
- End-to-end audit trail reconstruction

Developers should:
- Add new sample data as new features or edge cases are implemented
- Use these scenarios for manual and automated testing
- Document new scenarios in this section as the project evolves

This ensures robust validation and demo readiness from the start.

To prevent documentation from falling behind the codebase:
- Update relevant documentation files with every significant code or workflow change.
- Assign responsibility for documentation updates as part of each pull request or feature branch.
- Review documentation as part of code review and before merging.
- Use clear commit messages to indicate documentation changes.
- Periodically audit documentation for accuracy and completeness.

This ensures that all contributors and the AI coding assistant have access to the latest information.

To ensure code quality and reduce defects in critical modules (such as the Agent2Agent protocol and MCP server):
- All changes to these modules must undergo code review by at least one other contributor (AI or human).
- Pair programming is encouraged for complex or high-impact features.
- Use pull requests for all major changes, and require approval before merging.
- Reviewers should check for correctness, clarity, test coverage, and documentation updates.
- Document review outcomes and decisions in the changelog or dev diary.

This policy helps maintain high standards and shared understanding for the most important parts of the system.

To ensure steady progress and alignment, the team will:
- Conduct weekly standup meetings (in-person or async) to review the canonical build checklist in `/docs/TODO.md`.
- Use the checklist to track completed, in-progress, and blocked items.
- Assign action items and update blockers in a running changelog or dev diary.
- Encourage async check-ins via project chat or issue tracker for distributed contributors.
- Review and update the checklist at the start of each sprint or milestone.

This process ensures transparency, accountability, and continuous momentum throughout the project lifecycle.


## Model Selection Rationale & Update Process

### Rationale for Model and Technology Choices

- **Python 3.12**: Chosen for its strong ecosystem, rapid prototyping capabilities, and compatibility with AI/ML and data tools.
- **Streamlit**: Enables fast, interactive UI development in Python, ideal for demos and internal tools.
- **Azure AI Agents SDK**: Used for agent orchestration, leveraging cloud-based AI and secure integration with Azure resources.

**Azure AI SDK Tool Call Registration**: All agent tool calls (authorization, data lookup, notification, report generation) are implemented as Python async functions and registered with the agent using the Azure SDK. There is no REST MCP server; all orchestration and tool call execution is local and auditable. This ensures every agent action is modular, traceable, and compliant.

For the full MCP tool call protocol specification, see [`toolcalls.md`](toolcalls.md).
- **CSV Data Storage**: Selected for transparency, ease of manipulation, and suitability for prototyping and demos.
- **Pandas**: Used for robust, efficient CSV data access and manipulation.
- **python-dotenv**: Simplifies environment variable management for local and cloud deployments.

These choices prioritize rapid development, transparency, and ease of onboarding for new contributors, while ensuring the system is extensible and cloud-ready.

### Model/Component Update Process

1. **Review Requirements**: Reassess project requirements and stakeholder needs before considering a model or technology update.
2. **Evaluate Alternatives**: Research and compare new models, libraries, or frameworks for suitability, performance, and compatibility.
3. **Prototype & Test**: Implement a proof-of-concept or test integration in a feature branch. Validate with sample data and workflows.
4. **Document Changes**: Update `/docs/application.md` and `/docs/architecture.md` with rationale, migration steps, and any new dependencies.
5. **Code Review & Approval**: Submit changes via pull request. Require review and approval from at least one other contributor.
6. **Update Onboarding**: Revise `/docs/CONTRIBUTING.md` and `/docs/agentsetup.md` as needed to reflect new setup or usage instructions.
7. **Communicate & Train**: Announce changes in project meetings or chat, and provide guidance for contributors as needed.

This process ensures that all model and technology updates are transparent, justified, and well-documented, minimizing disruption and technical debt.

---


**Purpose:**  
Automate the detection, investigation, and advisory process for changes in business systems using a multi-agent AI architecture. All tool calls by agents are orchestrated as Python async functions registered with the agent using the Azure SDK. There is no REST MCP server; all orchestration, context management, and integration with data and notification services is handled locally in Python using async functions. This ensures every agent interaction is modular, auditable, and compliant, providing a unified interface for all tool calls and workflow orchestration.

**Core Value:**  
- Reduce manual effort in change governance  
- Accelerate resolution cycles  
- Ensure compliance and auditability  
- Provide clear, explainable decision trails


**Key Workflow:**  
1. **Trigger:** A new HR mutation entry triggers the Investigation Agent.
2. **Rights Check:** The Rights Check Agent verifies if the changer had the correct rights (via registered tool call). If authorized, the Investigation Agent sets the `change_investigation` column to 'Approved' in `hr_mutations.csv` for that change.  
3. **User Clarification:** If not approved, the Request for Information Agent contacts the changer for clarification and validates the response (via registered tool calls, e.g., checking sick leave or vacation data).  
4. **Manager Validation:** The Request for Information Agent contacts the manager to validate the changer’s claim (via registered tool call).  
5. **Advisory:** The Advisory Agent generates a report and recommendation for the Change Controller (via registered tool call), with three possible outcomes: (1) accept the change, (2) reject and initiate further investigation, or (3) mark as correct but requiring manual intervention.

---


## Detailed System Flow


This section describes the step-by-step flow of the agentic investigation and advisory process:

---

## Practical Multi-Agent Workflow Example

This example demonstrates how the multi-agent system processes a new HR mutation from start to finish, using sample data and showing each agent's actions and message flows.

### Example Scenario

- **User:** Alice (UserID: U123)
- **Application:** Payroll
- **Mutation:** Change salary for Bob (UserID: U456)
- **Reason:** "Correction after sick leave"

#### Step 1: HR Mutation Entry
- Alice submits a mutation via the UI.
- Entry is added to `hr_mutations.csv`:
	- `changer=U123`, `target=U456`, `application=Payroll`, `reason=Correction after sick leave`, `status=Pending`
- Audit trail logs: "Mutation submitted by Alice (U123) for Bob (U456) in Payroll."

#### Step 2: Investigation Agent Triggered
- Investigation Agent detects the new entry.
- Updates status to `Investigation Started`.
- Logs: "Investigation started for mutation X."

#### Step 3: Rights Check Agent
- Investigation Agent sends a message (via Agent2Agent protocol) to Rights Check Agent:
	- Context: mutation details, changer ID, application
	- Correlation ID: auto-generated
-- Rights Check Agent calls MCP server to check if Alice (U123) is authorized for this change.
-- MCP server queries `authorisations.csv` and `role_authorisations.csv`.
- Rights Check Agent returns result:
	- If authorized: Investigation Agent sets status to `Approved`, logs action, and process ends.
	- If not authorized: Investigation Agent sets status to `Clarification Requested`, logs action.

#### Step 4: Request for Information Agent (User Clarification)
- Investigation Agent sends a clarification request to Request for Information Agent.
-- Request for Information Agent calls MCP server to send a (mocked) notification to Alice.
-- Status set to `Awaiting User Response`.
-- Alice responds via UI (mocked response captured by MCP server).
-- Request for Information Agent validates claim (e.g., checks `sickLeave.csv` for Bob).
- If claim invalid: status set to `Rejected - Invalid User Claim`, logs action, process ends.
- If claim valid: status set to `Manager Verification Requested`, logs action.


# Workflow Example, User Stories, Audit Trail, and Status Codes

For a detailed workflow example, user stories, audit trail format, and status codes, see `/docs/architecture.md`.

This document focuses on onboarding, setup, deployment, and contributor guidance. For technical workflow, agent responsibilities, and audit/compliance details, refer to the architecture documentation.
- Run the MCP server (e.g., `python src/mcp_server.py`).
- Confirm endpoints are available (see API spec in `architecture.md`).

#### 3. Launch Agents
- Start the main orchestrator: `python src/agent_main.py`.
- Agents will be initialized and registered automatically.

#### 4. Start the Streamlit UI
- Run: `streamlit run src/ui.py` (or the relevant UI entrypoint).
- Access the UI in your browser (default: `localhost:8501`).


### Troubleshooting Tips
- If endpoints are not available, check server logs and port configuration.
- If agents fail to initialize, verify `.env` and data files.
- For UI issues, ensure Streamlit is installed and all dependencies are met.
- For data errors, check CSV file formats and required columns.

---

## Testing & Validation Strategy

### Test Plan
- **Unit Tests:** Test each agent class and MCP server endpoint in isolation.
- **Integration Tests:** Test agent workflows with sample data and mock tool calls.
- **End-to-End Tests:** Simulate a full HR mutation workflow from entry to advisory report.

### Sample Test Data & Expected Outcomes
- Use provided sample rows in documentation for each CSV file.
- Validate status transitions and audit trail logging for each workflow step.

### Mocking User/Manager Responses & Tool Calls
- All notifications and responses are mocked in the UI (no real email integration).
- Use UI forms/buttons to simulate user/manager responses.
- Tool calls to the MCP server can be mocked for testing error handling and edge cases.

---

## Data Model & CSV Schemas

# CSV Data Model Reference

For complete and canonical CSV schema definitions, including columns, types, constraints, and sample rows for all data files (`authorisations.csv`, `hr_mutations.csv`, `role_authorisations.csv`, `roles.csv`, `users.csv`, `sickLeave.csv`, `vacation.csv`, `audit_trail.csv`), see [`csv_schemas.md`](csv_schemas.md).

Reference this file for all data model details, onboarding, and validation requirements. Update `csv_schemas.md` if the data model evolves.


## Audit Logging and Compliance

--- Every agent action, UI mutation, and registered tool call is logged to `audit_trail.csv`.
- The audit trail includes: AuditID, MutationID, Timestamp, OldStatus, NewStatus, Agent, and Comment.
- Agents do not directly mutate state files; all state changes are orchestrated via the UI or registered tool calls, which are responsible for logging.
- Log rotation/archiving is implemented for large audit files.
- The function `get_audit_trail_for_mutation(mutation_id)` allows full traceability for any mutation.


This ensures compliance, traceability, and a clear, explainable decision trail for all system actions.
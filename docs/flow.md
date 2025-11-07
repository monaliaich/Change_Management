
# See Also
- [application.md](application.md): End-to-end workflow, agent responsibilities, status codes, CSV schemas, audit/logging, deployment & testing guidance
- [architecture.md](architecture.md): System architecture, Agent2Agent protocol, MCP server, sequence diagrams, toolcall mappings, module responsibilities
- [toolcalls.md](toolcalls.md): MCP tool call protocol and agent tool call details
- [csv_schemas.md](csv_schemas.md): Canonical CSV schemas and data model
- [README.md](README.md): Documentation index and onboarding

# End-to-End IT Change Validation Workflow: Implementation Flow

## 1. Overview
This document describes the canonical workflow and implementation plan for the IT Change Validation Pipeline, aligning data sources, validation steps, and exception handling. It incorporates the latest architectural choices: sequential validation, evidence retention, and AI-assisted exception recommendations. The workflow ensures compliance with ITSM approvals, CAB decisions, and CI/CD deployment logs.

## 2. High-Level Flow
A. Start with extracting population from Change DB.
B. Export approvals from ITSM Approvals.
C. Validate IPE (Integrity of Process Execution) against schema.
D. Reconcile ITSM dashboard.
E. If IPE validation fails:
     E.1. Log failure and alert.
     E.2. Trigger remediation workflow.
F. If IPE validation passes:
     Enter Validation Pipeline:
     F.1. Validate CI/CD vs ITSM logs.
     F.2. Validate assessment fields.
     F.3. Validate CAB/Owner approval pre-deploy.
     F.4. Validate evidence retention.
     F.5. Validate approver authorization (DOA).
     F.6. Validate approved window.
G. Handle exceptions: Log reason codes and generate AI recommendations.
H. Generate summary and provide justification.

3. **Detailed Implementation Steps** 
3.1. **Data Sources** 
    - Change DB - Columns: change_id, change_wi, CI_link
    - ITSM Approvals - Columns: approval_status, approval_time, approval_group
    - CI/CD Logs - Columns: deployment_id, pipeline_id, status, started_at, finished_at
    - Evidence Repository - Columns: retention_ref, retention_id
    - CAB Minutes - Columns: meeting_ref, decision_ref
    - DOA Register - Columns: approver_id, effective_from_to

3.2. **Validation Pipeline Steps** 
    - VALIDATE: CI/CD vs ITSM (Logged?)
    - VALIDATE: Assessment fields present
    - VALIDATE: CAB/Owner approval pre-deploy
    - VALIDATE: Approval evidence retained
    - VALIDATE: Approver authorized (DOA)
    - VALIDATE: Within approved window

3.3. **Exception Handling** 
     A. Decision point: Any exceptions?
       - Yes → Log exception with reason codes and AI-generated recommendation
       - No → Generate summary and detailed exception log
     B. Reviewer validates results and provides justification.

## 4. Example Workflow
1. Extract population from Change DB.
2. Export approvals from ITSM.
3. Validate IPE and reconcile ITSM dashboard.
4. If valid, proceed to sequential validation pipeline:
    - CI/CD vs ITSM logs
    - CAB approval checks
    - Evidence retention
    - DOA authorization
    - Approved window validation

5. Handle exceptions and generate AI recommendations.
6. Reviewer provides justification and closes workflow.

## 5. Summary Table: Component Responsibilities
| Component         | Responsibility                                    |
|-------------------|---------------------------------------------------|
| Change DB    | Source of change records |
| ITSM Approvals      | Approval status and timestamps   |
| CI/CD Logs            | Deployment and pipeline execution details        |
| Evidence Repository        | Retention of approval evidence                 |
| CAB Minutes       | Meeting decisions and references  |
| DOA Register      | Approver authorization validation |

## 6. Notes
- The "MCP server" is now a local Python orchestration pattern, not a REST API.
- All communication and workflow logic is handled in-process via Python functions and the Azure SDK.
- The UI is the primary interface for demo, audit, and user/manager interaction.
- This pattern is demo/test focused, not production-hardened.

---

**This document is the canonical flow for the demo. All contributors and AI coding agents should follow it for consistent, auditable, and extensible development.**

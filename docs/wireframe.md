
# See Also
- [application.md](application.md): End-to-end workflow, agent responsibilities, status codes, CSV schemas, audit/logging, deployment & testing guidance
- [architecture.md](architecture.md): System architecture, Agent2Agent protocol, MCP server, sequence diagrams, toolcall mappings, module responsibilities
- [flow.md](flow.md): Canonical workflow diagram
- [toolcalls.md](toolcalls.md): MCP tool call protocol and agent tool call details
- [csv_schemas.md](csv_schemas.md): Canonical CSV schemas and data model
- [README.md](README.md): Documentation index and onboarding

# UI Visuals and Screenshots

> Note: For the canonical UI workflow, see the Streamlit app in `src/ui.py`.

Add screenshots or UI mockups here as the UI evolves. Use the text-based wireframes below as a reference for layout and navigation.
# UI Wireframes for Multi-Agent Change Management Control System

This file provides text-based wireframes for the main UI pages, designed for implementation in Streamlit (Python). Each section describes the layout, navigation, and key UI elements.

---

## 1. Change Validation Entry Page

```
------------------------------------------------------
| Change Validation Entry                            |
------------------------------------------------------
| Change ID:     [Text Input]                        |
| CI Link:       [Text Input]                        |
| Approver Group:[Dropdown: Select Group]            |
| Reason:        [Text Input]                        |
| [Submit Button]                                    |
------------------------------------------------------
| [Success/Error Message]                            |
------------------------------------------------------
```

**Notes:**
- Submitting triggers the IPE validation workflow.
- All fields are required.

---

## 2. Change Validation Table

```
------------------------------------------------------
| Change Validation Table                            |
------------------------------------------------------
| [Filter: Status] [Filter: Approver] [Filter: Date] |
------------------------------------------------------
| ID | CI Link | Status | Approver | Date | [View]   |
|----|---------|--------|----------|------|--------  |
| .. | ....    | ...    | ...      | ...  | [Btn]    |
| .. | ....    | ...    | ...      | ...  | [Btn]    |
------------------------------------------------------
```

**Notes:**
- Clicking [View] opens the Audit Trail for that change.

---

## 3. Audit Trail Page

```
------------------------------------------------------
| Audit Trail for Change [ID]                        |
------------------------------------------------------
| Status Timeline:                                   |
| [Extracted] -> [Approvals Exported] -> [IPE Valid] |
------------------------------------------------------
| Timestamp | Step | Action/Status | Details         |
|-----------|------|--------------|----------------- |
| ...       | ...  | ...          | ...             |
------------------------------------------------------
| [Back to Table]                                    |
------------------------------------------------------
```

**Notes:**
- Shows all validation steps and data checks for the selected change.

---

## 4. Mocked User/Manager Response Page

```
------------------------------------------------------
| Handle Validation Exceptions                       |
------------------------------------------------------
| Exception: [Text of validation failure]            |
------------------------------------------------------
| [Text Input: Reason/Justification]                 |
| [Submit Response Button]                           |
------------------------------------------------------
| [Back to Audit Trail]                              |
------------------------------------------------------
```

**Notes:**
- Only shown when exceptions occur.
- Submitting updates the audit trail and status.

---

## 5. Insights/Dashboard Page

```
------------------------------------------------------
| Insights & Dashboard                               |
------------------------------------------------------
| [Metric: # Pending] [Metric: # Validated] ...      |
| [Chart: Status Distribution]                       |
| [Chart: Exception Frequency]                       |
| [Table: High-Risk Changes]                         |
------------------------------------------------------
```

**Notes:**
- Visualizes system health, validation status, and anomalies.

---

## 6. (Optional) Manual Trigger/Chat Page

```
------------------------------------------------------
| Manual Agent Trigger / Chat                        |
------------------------------------------------------
| [Dropdown: Select Agent]                           |
| [Text Input: Command/Message]                      |
| [Send Button]                                      |
| [Agent Response Output]                            |
------------------------------------------------------
```

**Notes:**
- For testing and debugging agent interactions.

---

## Navigation

- Sidebar or top menu with links to:
    - Change Validation Entry
    - Change Validation Table
    - Insights/Dashboard
    - (Optional) Manual Trigger/Chat

---

**How to use this wireframe:**
- Each section above maps directly to a Streamlit page or component.
- Use the layout and field names as a guide for building the UI.

- Adjust as needed for usability and aesthetics.
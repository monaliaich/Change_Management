# Appropriate IT or Business Change-Management Personnel Approve Migration of Changes to Production

This project implements an automated audit system for change management processes, focusing on segregation of duties (SOD) validation, approver authorization, and deployer verification. The system uses AI-powered agents to analyze change management data and identify compliance issues.

## Overview

The Change Management Audit Automation system consists of a data extraction agent and several AI-powered validation agents that work together to validate different aspects of the change management process:

1. **IdentifyChangeMigrationAgent**: Extracts and prepares the population of change management records for analysis (non-AI)
2. **ApproverValidationAgent**: Uses AI to validate if approvers have proper authorization
3. **DeployerValidationAgent**: Uses AI to validate if deployers have proper authorization
4. **SODViolationDetectionAgent**: Uses AI to detect segregation of duties violations

## Key Features

- AI-powered analysis using Azure AI Foundry for validation agents
- Data extraction and preparation through non-AI processing
- Asynchronous batch processing for efficient data handling
- Comprehensive validation against IAM user roles and DOA matrices
- Detailed reporting with exception reasons
- Flexible scheduling for periodic execution

## Architecture

The system follows a sequential architecture where data is first extracted and then analyzed:

```
┌─────────────────────┐     ┌─────────────────────┐
│ Workflow Scheduler  │────▶│ Audit Workflow      │
└─────────────────────┘     └──────────┬──────────┘
                                       │
                                       ▼
┌─────────────────────┐     ┌─────────────────────┐
│ Data Extractor      │────▶│ Identify Agent      │ (Non-AI data extraction)
└─────────────────────┘     └──────────┬──────────┘
                                       │
                                       │ Extracted Data
                                       ▼
                            ┌─────────────────────┐
                            │ AI-Powered Agents   │
                            │                     │
                            │ - SOD Agent         │
                            │ - Approver Agent    │
                            │ - Deployer Agent    │
                            └─────────────────────┘
```

## Agents

### IdentifyChangeMigrationAgent (Non-AI)

This agent is responsible for:
- Loading extraction parameters
- Extracting change migration data based on period and filters
- Validating and cleaning the data
- Computing record count and hash total
- Assembling metadata
- Saving the verified population file for use by AI agents

### ApproverValidationAgent (AI-Powered)

This agent uses Azure AI Foundry to:
- Load verified population data extracted by the Identify Agent
- Load IAM users data
- Validate approvers against IAM users list using AI analysis
- Check if approvers have the correct role
- Flag unauthorized approvers
- Generate a report with flagged records and reason codes

### DeployerValidationAgent (AI-Powered)

This agent uses Azure AI Foundry to:
- Load verified population data extracted by the Identify Agent
- Load CI/CD deployment logs
- Load IAM users data
- Validate deployers against IAM users list using AI analysis
- Check if deployers have the correct role
- Flag unauthorized deployers
- Generate a report with flagged records and reason codes

### SODViolationDetectionAgent (AI-Powered)

This agent uses Azure AI Foundry to:
- Load verified population data extracted by the Identify Agent
- Identify when the same person performs multiple roles
- Check for violations of role separation principles
- Generate violation reports with detailed reasons
- Save the violation report with metadata

## Workflow Execution

The system supports two execution modes:

1. **Single Execution**: Run a specific workflow once
2. **Scheduled Execution**: Run a workflow periodically at specified intervals

### Workflow Types

- **SOD Workflow**: Runs the identification agent to extract data, followed by the SOD violation detection agent
- **Approver Validation Workflow**: Runs the identification agent to extract data, followed by the approver validation agent
- **Deployer Validation Workflow**: Runs the identification agent to extract data, followed by the deployer validation agent

## Usage

```bash
python main.py --mode [run|schedule] --workflow [sod|approver|deployer] --interval 5 --duration 60
```

### Arguments

- `--mode`: Operation mode (`run` for single execution, `schedule` for periodic execution)
- `--workflow`: Workflow to execute (`sod`, `approver`, or `deployer`)
- `--interval`: Interval in minutes for periodic execution (default: 5)
- `--duration`: Duration in minutes to run the scheduler (default: 60, 0 for indefinite)

## Requirements

- Python 3.8+
- Azure AI Foundry client
- Azure CLI credentials
- Pandas
- Azure Identity

## Environment Variables

The following environment variables are required:
- `PROJECT_ENDPOINT`: Azure AI Foundry project endpoint
- `AGENT_MODEL_DEPLOYMENT_NAME`: Azure AI Foundry model deployment name

## Data Structure

The system expects the following data files:
- Change migration data
- IAM users data
- CI/CD deployment logs
- DOA matrix data

## Output

Each agent generates reports in Excel format with detailed findings and metadata:
- SOD violation reports
- Approver validation reports
- Deployer validation reports

## Logging

The system logs detailed information about its operations to both the console and a log file (`audit_agents.log`).
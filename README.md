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

## Azure AI Foundry (Project Endpoints)
- Create Resource Group
- Create AI Hub (Foundry)
- Create Project (Inside AI Hub - Foundry Project)
- Open "Go To Foundry Portal"
- Create MODEL + ENDPOINTS : GPT -4o
- Provide RBAC access inside Foundry project
     - Access Control IAM
     - View Access (search "Cognitive Services User")
     - Not present, then "Add Role Assignment"
     - Click Next, then assign it to: Your user (email) 
     - Click Review + assign

# Setting Up the Change Management Automation Project

This guide will help you set up and run the Change Management Automation project after pulling it from GitHub.

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.8 or higher
- Git
- Azure CLI

## Step 1: Clone the Repository

```bash
git clone https://github.com/monaliaich/Change_Management.git
cd Change_Management
```

## Step 2: Set Up a Virtual Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
#Powershell :
.\.venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Configure Azure AI Foundry

1. **Log in to Azure**
   ```bash
   az login
   ```

2. **Set up environment variables**
   
   Create a `.env` file in the project root with the following variables:
   ```
   PROJECT_ENDPOINT=your_foundry_project_endpoint
   AGENT_MODEL_DEPLOYMENT_NAME=your_model_deployment_name
   ```

## Step 5: Prepare Data Files

Ensure you have the required data files in the appropriate format:
- Place change migration data in the `data/input/` directory
- Place IAM users data in the `data/input/` directory
- Place CI/CD deployment logs in the `data/input/` directory
- Place DOA matrix data in the `data/input/` directory

## Step 6: Configure Azure AI Foundry Project

1. **Create Resource Group in Azure Portal**
2. **Create AI Hub (Foundry)**
3. **Create Project inside AI Hub**
4. **Open "Go To Foundry Portal"**
5. **Create MODEL + ENDPOINTS**
   - Select GPT-4o as the model
   - Note the endpoint URL for your `.env` file

6. **Provide RBAC access inside Foundry project**
   - Go to Access Control (IAM)
   - View Access (search "Cognitive Services User")
   - If not present, click "Add Role Assignment"
   - Click Next, then assign it to your user (email)
   - Click Review + assign

## Step 7: Run the Application

### For a single execution:

```bash
python src/main.py --workflow sod --mode run 

python src/main.py --workflow deployer --mode run

python src/main.py --workflow approver --mode run
```

### For scheduled execution:

```bash
python main.py --mode schedule --workflow sod --interval 5 --duration 60

python main.py --mode schedule --workflow deployer --interval 5 --duration 60

python main.py --mode schedule --workflow approver --interval 5 --duration 60
```

Available workflows:
- `sod`: Runs SOD violation detection
- `approver`: Runs approver validation
- `deployer`: Runs deployer validation

## Step 8: Check Results

After execution, check the output directory for generated reports:
```bash
ls data/output/
```

The reports will be in Excel format with detailed findings and metadata.

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Ensure you're logged in with Azure CLI: `az login`
   - Verify your user has the "Cognitive Services User" role in the Foundry project

2. **Missing Environment Variables**:
   - Check that your `.env` file or system environment variables are correctly set

3. **Data Format Issues**:
   - Ensure your input data files follow the expected format
   - Check the logs for any data validation errors

### Logging

The system logs detailed information to both the console and a log file:
```bash
cat audit_agents.log
```
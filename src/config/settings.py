# config/settings.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Agent configuration
AGENT_NAME = "IdentifyChangeMigrationAgent"
AGENT_DESCRIPTION = "Agent for identifying and validating change migration events"

# Schedule configuration
SCHEDULE_INTERVAL_MINUTES = int(os.getenv("SCHEDULE_INTERVAL_MINUTES", "60"))  # Default to hourly

# Data paths
DATA_INPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "input")
DATA_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "output", "verified_populations")
print(f"Data input path: {DATA_INPUT_PATH}")
print(f"Data output path: {DATA_OUTPUT_PATH}")

# Extraction Parameter file path
PARAMETER_FILE_PATH = os.path.join(DATA_INPUT_PATH, "extraction_parameters.csv")


# Column validations
REQUIRED_COLUMNS = {
    "change_migration_listing": [
        "Change_ID", "Title", "Change_Type", "Risk_Rating", 
        "Requestor", "Approver", "Migration_DateTime", 
        "Deployment_Method", "Status", "Source_System"
    ],
    "extraction_parameters": [
        "client_name", "start_date", "end_date", "system_type"
    ]
}

# Validation rules
VALIDATION_RULES = {
    "Change_ID": {"unique": True, "null": False},
    "Migration_DateTime": {"date_range": True},
    "Risk_Rating": {"allowed_values": ["High", "Medium", "Low", "H", "M", "L"]},
    "Change_Type": {"allowed_values": ["application", "infrastructure", "configuration", "app", "infra", "config"]},
    "Status": {"allowed_values": ["Completed", "Closed", "Deployed", "Rolled Back"]}
}

# Metadata fields
METADATA_FIELDS = [
    "extraction_timestamp",
    "extracted_by",
    "start_date",
    "end_date",
    "system_name",
    "record_count",
    "hash_total",
    "parameter_file_used"
]


# Ensure output directory exists
true = os.makedirs(DATA_OUTPUT_PATH, exist_ok=True)
print(f"Output directory created: {true}")
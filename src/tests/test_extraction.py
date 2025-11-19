import os
from identify_change_migration_agent import IdentifyChangeMigrationAgent
import pandas as pd

def test_sap_extraction():
    """Test extraction for SAP system for a specific period."""
    # Create test parameters
    os.makedirs("data", exist_ok=True)
    
    # Create test parameters file
    test_params = {
        "Client Name": ["TestClient"],
        "Start Date": ["2023-01-01"],
        "End Date": ["2023-03-31"],
        "System Type": ["SAP"]
    }
    params_df = pd.DataFrame(test_params)
    params_df.to_excel("data/extraction_parameters.xlsx", index=False)
    
    # Run the agent
    agent = IdentifyChangeMigrationAgent()
    agent.load_extraction_parameters()
    migration_data = agent.extract_change_migration_list()
    
    # Print results
    if migration_data is not None:
        print(f"Successfully extracted {len(migration_data)} records for SAP system")
        print("\nSample data (first 5 rows):")
        print(migration_data.head())
    else:
        print("No records found for the specified period and system")
    
    return migration_data

if __name__ == "__main__":
    test_sap_extraction()
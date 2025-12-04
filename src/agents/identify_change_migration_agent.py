# agents/IdentifyChangeMigrationAgent.py
# agents/identify_change_migration_agent.py
import os
import logging
import sys
import pandas as pd
from datetime import datetime as dt
import hashlib
import json
import logging
from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential
from utils.parameter_loader import ExtractionParameterLoader
from utils.data_validator import DataValidator
from config.settings import DATA_INPUT_PATH, DATA_OUTPUT_PATH, PARAMETER_FILE_PATH, METADATA_FIELDS

class IdentifyChangeMigrationAgent:
    """
    Agent responsible for identifying and validating change migration events.
    
    This agent performs the following tasks:
    1. Load extraction parameters
    2. Extract change-migration list based on period and filters
    3. Validate and clean the data
    4. Compute record count and hash total
    5. Assemble metadata
    6. Save verified population file
    """
    logger = logging.getLogger(__name__)
    logger.info("This is a log message.")

    def __init__(self, data_dir="./data/input", output_data_dir="./data/output"):
        self.name = "IdentifyChangeMigrationAgent"
        self.logger = logging.getLogger(self.name)
        self.data_dir = data_dir
        self.output_data_dir=output_data_dir
        self.extraction_params = None
        self.parameters = {}  # Initialize as empty dictionary
        self.migration_data = None
        self.change_data = None
        self.metadata = {}
        self.parameter_loader = ExtractionParameterLoader(PARAMETER_FILE_PATH)

        # Validate required environment variables
        required = ["PROJECT_ENDPOINT", "AGENT_MODEL_DEPLOYMENT_NAME"]
        missing = [k for k in required if not os.environ.get(k)]
        if missing:
            self.logger.error("Missing env vars: %s", ", ".join(missing))
            sys.exit(2)

        # If validation passes, continue with your setup
        self.PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT")
        self.AGENT_MODEL_DEPLOYMENT_NAME = os.environ.get("AGENT_MODEL_DEPLOYMENT_NAME")

        # Initialize Azure AI Foundry client
        client = AgentsClient(
        endpoint=self.PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
            )
        )

    def deploy_to_foundry(self, model_name="IdentifyChangeMigrationAgent"):
        """
        Deploy the agent to Azure AI Foundry.
        """
        try:
            self.logger.info(f"Deploying agent to Azure AI Foundry as {model_name}")
            
            # Create a model package
            model_package = self.client.models.create_or_update(
                name=model_name,
                description="Agent for identifying change migration population",
                version="1.0.0"
            )
            
            # Deploy the model
            deployment = self.client.deployments.create_or_update(
                name=self.AGENT_MODEL_DEPLOYMENT_NAME,
                model=model_package.id,
                compute_type="Standard_DS3_v2",
                instance_count=1
            )
            
            self.logger.info(f"Agent deployed successfully. Endpoint: {deployment.endpoint}")
            return deployment.endpoint
            
        except Exception as e:
            self.logger.error(f"Error deploying to Azure AI Foundry: {str(e)}")
            raise

    def load_extraction_parameters(self):
        """
        Load extraction parameters from the parameter file.
        """
        
        try:
            self.logger.info(f"Loading extraction parameters from {self.data_dir}")
            param_file = os.path.join(self.data_dir, "extraction_parameters.xlsx")
            
            if not os.path.exists(param_file):
                self.logger.error(f"Parameter file not found at {param_file}")
                return False
            
            self.logger.info(f"Parameter file found at {param_file}")
            df = pd.read_excel(param_file)

            # If the file has multiple rows, use the first row
            if len(df) > 0:
                self.parameters = df.iloc[0].to_dict()
            else:
                self.parameters = {}

            # Store parameter metadata
            self.metadata["extraction_parameters"] = self.parameters.copy()
            self.metadata["parameter_file"] = os.path.basename(param_file)
        
            self.logger.info(f"Loaded parameters: {self.parameters}")
            return True    
        
        except Exception as e:
            self.logger.error(f"Error loading extraction parameters: {str(e)}")
            self.parameters = {}  # Ensure parameters is at least an empty dict
            return False

    def extract_change_migration_list(self):
        """
        Extracts the change migration list based on the loaded parameters.
    
        Returns:
            pandas.DataFrame: The filtered change migration data
        """
        try:
            self.logger.info("Extracting change migration list")

            # Ensure parameters exist
            if not hasattr(self, 'parameters') or self.parameters is None:
                self.parameters = {}
                self.logger.warning("Parameters not initialized, using empty dictionary")

            # Load the change migration data
            migration_data_path = os.path.join(self.data_dir, "c1_change_migration_population_v1.csv")
            if not os.path.exists(migration_data_path):
                raise FileNotFoundError(f"Change migration data file not found at {migration_data_path}")
            
            # CSV uses semicolon as delimiter; read with explicit separator
            migration_data = pd.read_csv(migration_data_path, sep=';')
            self.logger.info(f"Loaded {len(migration_data)} records from change migration data")          
            self.logger.info(f"columns in migration data:  {migration_data.columns}")

            # Check if required columns exist (use names normalized above) #Implementation_Timestamp
            required_columns = ['Implementation_Timestamp', 'Asset_Name']
            missing_columns = [col for col in required_columns if col not in migration_data.columns]
        
            if missing_columns:
                self.logger.error(f"Missing required columns in data: {missing_columns}")
                return False
        
            # Apply filters based on extraction parameters
            filtered_data = migration_data.copy()

            # Filter by date range if provided
            if 'Start Date' in self.parameters and 'End Date' in self.parameters:
                start_date = pd.to_datetime(self.parameters['Start Date'], format='%d-%m-%Y %H:%M', errors='coerce')
                end_date = pd.to_datetime(self.parameters['End Date'], format='%d-%m-%Y %H:%M', errors='coerce')
                self.logger.info(f"Parsed start_date: {start_date}, end_date: {end_date}")

                # Ensure migration date is in datetime format
                try:
                    filtered_data['Implementation_Timestamp_DT'] = pd.to_datetime(
                        filtered_data['Implementation_Timestamp'], 
                        format='%d-%m-%Y %H:%M', 
                        errors='coerce'
                    )
                    
                    # Drop rows with invalid dates
                    invalid_dates = filtered_data['Implementation_Timestamp_DT'].isna()

                    if invalid_dates.any():
                        self.logger.warning(f"Dropping {invalid_dates.sum()} rows with invalid dates")
                        filtered_data = filtered_data.dropna(subset=['Implementation_Timestamp_DT'])


                    # Filter by date range
                    filtered_data = filtered_data[
                        (filtered_data['Implementation_Timestamp_DT'] >= start_date) & 
                        (filtered_data['Implementation_Timestamp_DT'] <= end_date)
                    ]
                    
                    self.logger.info(f"Filtered by date range: {start_date} to {end_date}, records remaining: {len(filtered_data)}")     

                except Exception as e:
                    self.logger.error(f"Error processing Migration Date: {str(e)}")               
                
            # Filter by Asset Name if provided
            if 'Asset Name' in self.parameters and self.parameters['Asset Name']:
                asset_names = self.parameters['Asset Name'].split(',')
                asset_names = [s.strip() for s in asset_names]

                self.logger.info(f"Asset names to filter: {asset_names}")
                self.logger.info(f"Unique Asset_Name values in data: {filtered_data['Asset_Name'].unique().tolist()}")

                before_count = len(filtered_data)
                filtered_data = filtered_data[filtered_data['Asset_Name'].isin(asset_names)]
                after_count = len(filtered_data)
                self.logger.info(f"Filtered by asset names: {asset_names}, records before: {before_count}, after: {after_count}")

            # Check if we have any records after filtering
            if len(filtered_data) == 0:
                self.logger.warning("No records found for the specified period and filters")
                self.migration_data = None
                return False 

            # Explicitly set self.migration_data
            self.migration_data = filtered_data.copy()           
            self.logger.info(f"Set self.migration_data with {len(self.migration_data)} records")
    
            return filtered_data         

        except Exception as e:
            self.logger.error(f"Error extracting change migration list: {str(e)}")
            raise  


    def validate_and_clean_data(self):
        """
        Validates and cleans the extracted migration data.
        """
        if self.migration_data is None or len(self.migration_data) == 0:
            self.logger.warning("No data to validate and clean")
            return False
        
        try:
            self.logger.info("Validating and cleaning data")
        
            # Create extraction parameters dictionary for the validator
            extraction_params = {
                "date_range": {
                    "start_date": self.parameters.get('Start Date'),
                    "end_date": self.parameters.get('End Date')
                },
                "source_system": self.parameters.get('Asset Name')
            }
        
            self.logger.info(f"Using extraction parameters for validation: {extraction_params}")
            
            # Create validator with data and parameters
            validator = DataValidator(data=self.migration_data, extraction_params=extraction_params)
            # Run validation
            validation_results = validator.validate()

            # Store validation results in metadata
            self.metadata['validation_results'] = {
                'is_valid': validation_results['is_valid'],
                'errors': validation_results['errors'],
                'warnings': validation_results['warnings']
            }

            # Log validation results
            if not validation_results['is_valid']:
                self.logger.warning(f"Data validation failed: {validation_results['errors']}")
                if validation_results['warnings']:
                    self.logger.info(f"Validation warnings: {validation_results['warnings']}")
            else:
                self.logger.info("Data validation passed")
                if validation_results['warnings']:
                    self.logger.info(f"Validation warnings: {validation_results['warnings']}")


            # Get cleaned data
            self.migration_data = validator.get_clean_data()
            self.logger.info(f"Data cleaned. {len(self.migration_data)} records remaining.")
        
            return True        
            
        except Exception as e:
            self.logger.error(f"Error validating and cleaning data: {str(e)}")
            raise  


    def compute_record_count_and_hash(self):
            """
            Computes record count and hash total for the migration data.
            """
            if self.migration_data is None or len(self.migration_data) == 0:
                self.logger.warning("No data to compute record count and hash")
                return False
        
            try:
                self.logger.info("Computing record count and hash total")
            
                # Record count
                record_count = len(self.migration_data)
                self.metadata['record_count'] = record_count
            
                # Hash total
                # Convert dataframe to string and compute hash
                data_string = self.migration_data.to_csv(index=False)
                hash_total = hashlib.sha256(data_string.encode()).hexdigest()
                self.metadata['hash_total'] = hash_total
            
                self.logger.info(f"Record count: {record_count}, Hash total: {hash_total}")
                return True
            
            except Exception as e:
                self.logger.error(f"Error computing record count and hash: {str(e)}")
                raise    

    def assemble_metadata(self):
            """
            Assembles metadata for the verified population file.
            """
            
            try:
                self.logger.info("Assembling metadata")
        
                # Add timestamp
                self.metadata['extraction_timestamp'] = dt.now().strftime('%Y-%m-%d %H:%M:%S')
                print (f"DateTimeStamp {self.metadata['extraction_timestamp']}")
                # Add extracted by
                self.metadata['extracted_by'] = 'IdentifyChangeMigrationAgent'
            
                # Add system name
                self.metadata['asset_name'] = self.parameters.get('Asset Name', 'All')
            
                # Add environment
                self.metadata['environment'] = 'Development'
            
                self.logger.info(f"Metadata assembled: {self.metadata}")
                return True
            
            except Exception as e:
                self.logger.error(f"Error assembling metadata: {str(e)}")
                raise       

    def save_verified_population_file(self):
            """
            Saves the verified population file with data and metadata.
            """
            if self.migration_data is None or len(self.migration_data) == 0:
                self.logger.warning("No data to save")
                return False
        
            try:
                self.logger.info("Saving verified population file")
            
                # Create output directory if it doesn't exist
                output_dir = os.path.join(self.output_data_dir, "verified_populations")
                os.makedirs(output_dir, exist_ok=True)
                
                self.logger.info(f"Absolute output_dir path of output file: {output_dir}")

                # Generate filename WITHOUT timestamp
                # timestamp = dt.now().strftime('%Y%m%d_%H%M%S')  # REMOVE THIS LINE
                client_name = self.parameters.get('Client Name', 'client')
                # CHANGE THIS LINE:
                filename = f"{client_name}_verified_population.xlsx"  # Removed timestamp
                output_path = os.path.join(output_dir, filename)
            
                # Create Excel writer
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    # Write data to sheet1
                    self.migration_data.to_excel(writer, sheet_name='Population Data', index=False)
        
                    # Write metadata to sheet2
                    metadata_df = pd.DataFrame(list(self.metadata.items()), columns=['Key', 'Value'])
                    metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
    
                self.logger.info(f"Verified population file saved to {output_path}")
                return output_path
            
            except Exception as e:
                self.logger.error(f"Error saving verified population file: {str(e)}")
                raise       

    def run(self):
        """
        Runs the complete agent workflow.
        """
        try:
            self.logger.info("Starting IdentifyChangeMigrationAgent")
            
            # Step 1: Load extraction parameters
            success = self.load_extraction_parameters()
            if not success:
                self.logger.error("Failed to load extraction parameters")
                return False
            
            # Verify parameters were loaded
            if not self.parameters:
                self.logger.error("Parameters were not loaded properly")
                return False
            
            self.logger.info(f"Using parameters: {self.parameters}")
            
            # Step 2: Extract change migration list
            migration_data = self.extract_change_migration_list()
            self.logger.info(f"Using Migration Data: {self.migration_data}")
            if self.migration_data is None or len(self.migration_data) == 0:
                self.logger.warning("No records found for the specified period and filters")
                return False
            
            # Step 3: Validate and clean data
            self.validate_and_clean_data()
            
            # Step 4: Compute record count and hash total
            self.compute_record_count_and_hash()
            
            # Step 5: Assemble metadata
            self.assemble_metadata()
            
            # Step 6: Save verified population file
            output_file = self.save_verified_population_file()
            
            self.logger.info(f"IdentifyChangeMigrationAgent completed successfully. Output file: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error running IdentifyChangeMigrationAgent: {str(e)}")
            return False

# Example usage
if __name__ == "__main__":
    agent = IdentifyChangeMigrationAgent()
    agent.run()              
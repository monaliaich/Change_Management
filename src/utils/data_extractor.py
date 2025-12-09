import os
import logging
import pandas as pd
from datetime import datetime as dt

logger = logging.getLogger(__name__)

class DataExtractor:
    """
    Utility class for extracting data from various sources.
    This class centralizes all data extraction logic for reuse across agents.
    """
    
    def __init__(self, data_dir="./data/input", output_data_dir="./data/output"):
        self.data_dir = data_dir
        self.output_data_dir = output_data_dir
        self.logger = logging.getLogger(__name__)
    
    def load_verified_population_data(self, verified_population_file=None):
        """
        Load change migration population data from verified population file.
        
        Args:
            verified_population_file: Path to the verified population file. If None,
                                     will look for the default file.
        
        Returns:
            tuple: (data, metadata, success)
                - data: DataFrame containing the population data
                - metadata: Dictionary containing metadata
                - success: Boolean indicating if the operation was successful
        """
        try:
            self.logger.info("Loading verified population data")
            
            if not verified_population_file:
                # Find the verified population file with constant name
                verified_pop_dir = os.path.join(self.output_data_dir, "verified_populations")
                if not os.path.exists(verified_pop_dir):
                    self.logger.error(f"Verified populations directory not found at {verified_pop_dir}")
                    return None, {}, False
                
                # Look for any file ending with "_verified_population.xlsx"
                population_files = [f for f in os.listdir(verified_pop_dir) 
                               if f.endswith("_verified_population.xlsx")]
                
                if not population_files:
                    self.logger.error(f"No verified population files found in {verified_pop_dir}")
                    return None, {}, False
                
                # Sort by modification time (newest first)
                population_files.sort(key=lambda x: os.path.getmtime(
                    os.path.join(verified_pop_dir, x)), reverse=True)
                
                # Use the most recent file
                verified_population_file = os.path.join(verified_pop_dir, population_files[0])
                self.logger.info(f"Using most recent verified population file: {verified_population_file}")
            
            # Load the Excel file
            self.logger.info(f"Loading data from {verified_population_file}")

            # Check if file exists
            if not os.path.exists(verified_population_file):
                self.logger.error(f"File does not exist: {verified_population_file}")
                return None, {}, False
            
            # Load data from the Population Data sheet
            try:
                data = pd.read_excel(verified_population_file, sheet_name='Population Data')

                # Check if data is empty
                if data is None or data.empty:
                    self.logger.error("Population Data sheet is empty or could not be read")
                    return None, {}, False
                
                # Check if required columns exist in change migration data
                required_columns = ['Change_ID', 'Asset_Name', 'Requestor_ID', 'Approver_ID', 'Developer_ID']
                missing_columns = [col for col in required_columns if col not in data.columns]

                if missing_columns:
                    self.logger.error(f"Missing required columns in change migration data: {missing_columns}")
                    return None, {}, False
                
                self.logger.info(f"Loaded {len(data)} records from verified population data")

                # Load metadata from the Metadata sheet
                metadata = {}
                try:
                    metadata_df = pd.read_excel(verified_population_file, sheet_name='Metadata')

                    # Convert metadata to dictionary
                    for _, row in metadata_df.iterrows():
                        key = row['Key']
                        value = row['Value']
                        metadata[key] = value
                
                    self.logger.info(f"Loaded metadata from verified population file")

                except Exception as e:
                    self.logger.warning(f"Error loading metadata sheet: {str(e)}")
                    # Continue even if metadata can't be loaded
                
                return data, metadata, True

            except Exception as e:
                self.logger.error(f"Error reading Excel file: {str(e)}")
                return None, {}, False
            
        except Exception as e:
            self.logger.error(f"Error loading verified population data: {str(e)}")
            return None, {}, False
    
    def load_cicd_deployment_logs(self):
        """
        Load deployment log data.
        
        Returns:
            tuple: (data, success)
                - data: DataFrame containing the deployment log data
                - success: Boolean indicating if the operation was successful
        """
        try:
            self.logger.info("Loading deployment log data")
            
            # Load the deployment log data
            file_path = os.path.join(self.data_dir, "c1_ci_cd_deployment_log_v1.csv")
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Deployment log data file not found at {file_path}")
            
            # Load CSV file
            data = pd.read_csv(file_path, sep=';')
            self.logger.info(f"Actual columns in file: {list(data.columns)}")
            self.logger.info(f"Loaded {len(data)} records from deployment log data")
            
            # Check if required columns exist
            required_columns = ['Linked_Change_ID', 'Asset_Name', 'Deployer_ID', 'Deployer_Name']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                self.logger.error(f"Missing required columns in deployment log data: {missing_columns}")
                return None, False
            
            self.logger.info(f"Deployment log data loaded with {len(data)} records")
            return data, True
            
        except Exception as e:
            self.logger.error(f"Error loading deployment log data: {str(e)}")
            return None, False
    
    def load_doa_matrix_data(self):
        """
        Load DOA (Delegation of Authority) matrix data.
        
        Returns:
            tuple: (data, success)
                - data: DataFrame containing the DOA matrix data
                - success: Boolean indicating if the operation was successful
        """
        try:
            self.logger.info("Loading DOA matrix data")
            
            # Load the DOA matrix data
            file_path = os.path.join(self.data_dir, "C1_DOAs_MAtrix_V1.csv")
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"DOA matrix data file not found at {file_path}")
            
            # Load CSV file
            data = pd.read_csv(file_path, sep=';')
            self.logger.info(f"Actual columns in file: {list(data.columns)}")
            self.logger.info(f"Loaded {len(data)} records from DOA matrix data")
            
            # Check if required columns exist
            required_columns = ['Role', 'Authorized_Applications', 'Risk_Threshold']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                self.logger.error(f"Missing required columns in DOA matrix data: {missing_columns}")
                return None, False
            
            self.logger.info(f"DOA matrix data loaded with {len(data)} records")
            return data, True
            
        except Exception as e:
            self.logger.error(f"Error loading DOA matrix data: {str(e)}")
            return None, False
    
    def load_iam_users_data(self):
        """
        Load IAM users status data.
        
        Returns:
            tuple: (data, success)
                - data: DataFrame containing the IAM users data
                - success: Boolean indicating if the operation was successful
        """
        try:
            self.logger.info("Loading IAM users status data")
            
            # Load the IAM users data
            file_path = os.path.join(self.data_dir, "c1_iam_users_status_v1.csv")
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"IAM users status data file not found at {file_path}")
            
            # Load CSV file
            data = pd.read_csv(file_path, sep=';')
            self.logger.info(f"Actual columns in file: {list(data.columns)}")
            # Check if required columns exist
            required_columns = ['User_ID', 'IAM_Role', 'Mapped_DOA_Role']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                self.logger.error(f"Missing required columns in IAM users status data: {missing_columns}")
                return None, False
            
            self.logger.info(f"IAM users status data loaded with {len(data)} records")
            return data, True
            
        except Exception as e:
            self.logger.error(f"Error loading IAM users status data: {str(e)}")
            return None, False
    
    def load_change_migration_data(self):
        """
        Load raw change migration data.
        
        Returns:
            tuple: (data, success)
                - data: DataFrame containing the change migration data
                - success: Boolean indicating if the operation was successful
        """
        try:
            self.logger.info("Loading change migration data")
            
            # Load the change migration data
            file_path = os.path.join(self.data_dir, "c1_change_migration_population_v1.csv")
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Change migration data file not found at {file_path}")
            
            # Load CSV file
            data = pd.read_csv(file_path, sep=';')
            self.logger.info(f"Actual columns in file: {list(data.columns)}")
            self.logger.info(f"Loaded {len(data)} records from change migration data")
            
            # Check if required columns exist
            required_columns = ['Change_ID', 'Asset_Name', 'Implementation_Timestamp', 'Approver_ID']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                self.logger.error(f"Missing required columns in change migration data: {missing_columns}")
                return None, False
            
            self.logger.info(f"Change migration data loaded with {len(data)} records")
            return data, True
            
        except Exception as e:
            self.logger.error(f"Error loading change migration data: {str(e)}")
            return None, False
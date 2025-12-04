# utils/parameter_loader.py
import os
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ExtractionParameterLoader:
    """
    Utility class for loading extraction parameters from Excel file
    """
    
    def __init__(self, parameter_file_path):
        self.parameter_file_path = parameter_file_path
        self.parameters = None
        
    def load_parameters(self):
        """Load extraction parameters from Excel file"""
        logger.info(f"Loading extraction parameters from {self.parameter_file_path}")
        
        try:
            if not os.path.exists(self.parameter_file_path):
                logger.warning(f"Parameter file not found: {self.parameter_file_path}")
                return None
            
            # Load the Excel file
            if self.parameter_file_path.endswith('.xlsx'):
                df = pd.read_excel(self.parameter_file_path)
            elif self.parameter_file_path.endswith('.csv'):
                df = pd.read_csv(self.parameter_file_path)
            else:
                logger.error(f"Unsupported file format: {self.parameter_file_path}")
                return None
            
            # Validate required columns
            required_columns = ['client_name', 'start_date', 'end_date', 'asset_name']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.error(f"Missing required columns in parameter file: {missing_columns}")
                return None
            
            # Process parameters
            parameters = []
            for _, row in df.iterrows():
                # Convert dates to proper format
                try:
                    start_date = pd.to_datetime(row['start_date']).strftime('%Y-%m-%d')
                    end_date = pd.to_datetime(row['end_date']).strftime('%Y-%m-%d')
                except Exception as e:
                    logger.error(f"Error parsing dates: {str(e)}")
                    continue
                
                # Create parameter entry
                param = {
                    'client_name': row['client_name'],
                    'date_range': {
                        'start_date': start_date,
                        'end_date': end_date
                    },
                    'systems': [s.strip() for s in str(row['asset_name']).split(',')],
                    'timestamp': datetime.now().isoformat(),
                    'extracted_by': 'IdentifyChangeMigrationAgent',
                    'parameter_file_used': os.path.basename(self.parameter_file_path)
                }
                
                parameters.append(param)
            
            self.parameters = parameters
            logger.info(f"Loaded {len(parameters)} parameter sets")
            return parameters
            
        except Exception as e:
            logger.error(f"Error loading parameters: {str(e)}")
            return None
    
    def get_parameters(self):
        """Get the loaded parameters or load them if not loaded yet"""
        if self.parameters is None:
            return self.load_parameters()
        return self.parameters
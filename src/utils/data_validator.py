# utils/data_validator.py
import pandas as pd
import logging
from config.settings import VALIDATION_RULES

logger = logging.getLogger(__name__)

class DataValidator:
    """
    Utility class for validating change migration data
    """
    def __init__(self, data, extraction_params=None):
        self.data = data
        self.extraction_params = extraction_params
        self.validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }

    def _validate_mandatory_fields(self):
        """Validate that all mandatory fields are present and not null"""
        mandatory_fields = ['Implementation_Timestamp', 'Asset_Name', 'Change_Type', 'Approver_ID']
    
        for field in mandatory_fields:
            if field not in self.data.columns:
                self.validation_results["errors"].append(f"Mandatory field {field} is missing")
                continue
            
            null_count = self.data[field].isnull().sum()
            if null_count > 0:
                self.validation_results["errors"].append(f"Found {null_count} null values in mandatory field {field}")
    
    def validate(self):
        """Run all validations on the data"""
        logger.info("Starting data validation")

        if self.data is None or self.data.empty:
            self.validation_results["is_valid"] = False
            self.validation_results["errors"].append("No data to validate")
            logger.warning("No data to validate")
            return self.validation_results
        
        # Run all validation checks
        self._validate_mandatory_fields()
        self._validate_unique_change_id()

        # Only validate date range if extraction parameters include date range
        if self.extraction_params and "date_range" in self.extraction_params and \
        self.extraction_params["date_range"].get("start_date") and \
        self.extraction_params["date_range"].get("end_date"):
            self._validate_date_range()
        else:
            logger.info("Date range parameters not provided or empty, skipping date range validation")
            self.validation_results["warnings"].append("Date range not specified, skipping validation")    

        # Only validate asset name if extraction parameters include asset name
        if self.extraction_params and "asset_name" in self.extraction_params and \
        self.extraction_params["asset_name"]:
            self._validate_asset_name()
        else:
            logger.info("Asset name parameter not provided or empty, skipping asset name validation")
            self.validation_results["warnings"].append("Asset name not specified, skipping validation")
        
        
        self._validate_allowed_values()
        self._validate_record_count()
        
        if self.validation_results["errors"]:
            self.validation_results["is_valid"] = False
            
        logger.info(f"Validation completed. Valid: {self.validation_results['is_valid']}")
        if self.validation_results["errors"]:
            logger.warning(f"Validation errors: {len(self.validation_results['errors'])}")
        if self.validation_results["warnings"]:
            logger.info(f"Validation warnings: {len(self.validation_results['warnings'])}")
            
        return self.validation_results   

    
    def _validate_asset_name(self):
        """Validate that Asset Name matches the requested parameter value"""
        if "Asset_Name" not in self.data.columns:
            self.validation_results["errors"].append("Asset_Name column is missing")
            return
        
        # Skip validation if asset name parameter is not provided or empty
        if not self.extraction_params or "asset_name" not in self.extraction_params or not self.extraction_params["asset_name"]:
            logger.info("Asset name parameter not provided or empty, skipping validation")
            return
        
        requested_asset = self.extraction_params["asset_name"]

        # comparison for single asset
        mismatched = self.data[self.data["Asset_Name"] != requested_asset]
    
        if len(mismatched) > 0:
            self.validation_results["errors"].append(
                f"Found {len(mismatched)} records with Asset_Name not matching the requested asset: {requested_asset}"
            )
     
    
    def _validate_unique_change_id(self):
        """Validate that Change_ID is unique"""
        if "Change_ID" not in self.data.columns:
            self.validation_results["errors"].append("Change_ID column is missing")
            return
        
        # Check for null values
        null_ids = self.data["Change_ID"].isnull().sum()
        if null_ids > 0:
            self.validation_results["errors"].append(f"Found {null_ids} null Change_ID values")
        
        # Check for duplicates
        duplicate_ids = self.data["Change_ID"].duplicated().sum()
        if duplicate_ids > 0:
            self.validation_results["errors"].append(f"Found {duplicate_ids} duplicate Change_ID values")
    
    
    def _validate_date_range(self):
        """Validate that Migration_DateTime is within the specified period"""
        if "Migration_DateTime" not in self.data.columns:
            self.validation_results["errors"].append("Migration_DateTime column is missing")
            return
        
        # Skip validation if date range parameters are not provided or empty
        if not self.extraction_params or "date_range" not in self.extraction_params or \
        not self.extraction_params["date_range"].get("start_date") or \
        not self.extraction_params["date_range"].get("end_date"):
            logger.info("Date range parameters not provided or empty, skipping validation")
            return
        
        # Convert to datetime if not already
        if not pd.api.types.is_datetime64_dtype(self.data["Migration_DateTime"]):
            try:
                self.data["Migration_DateTime"] = pd.to_datetime(self.data["Migration_DateTime"])
            except Exception as e:
                self.validation_results["errors"].append(f"Failed to convert Migration_DateTime to datetime: {str(e)}")
                return
        
        # Check date range
        start_date = pd.to_datetime(self.extraction_params["date_range"]["start_date"])
        end_date = pd.to_datetime(self.extraction_params["date_range"]["end_date"])
        
        out_of_range = ((self.data["Migration_DateTime"] < start_date) | 
                         (self.data["Migration_DateTime"] > end_date)).sum()
        
        if out_of_range > 0:
            self.validation_results["errors"].append(
                f"Found {out_of_range} records with Migration_DateTime outside the specified range"
            )
    
    def _validate_allowed_values(self):
        """Validate fields with allowed values"""
        for field, rules in VALIDATION_RULES.items():
            if "allowed_values" in rules and field in self.data.columns:
                allowed_values = rules["allowed_values"]
                invalid_values = self.data[~self.data[field].isin(allowed_values)][field].unique()
                
                if len(invalid_values) > 0:
                    self.validation_results["errors"].append(
                        f"Found invalid values in {field}: {list(invalid_values)}"
                    )
    
    def _validate_record_count(self):
        """Validate that there are records in the dataset"""
        record_count = len(self.data)
        if record_count == 0:
            self.validation_results["errors"].append("No records found in the dataset")
        else:
            logger.info(f"Record count validation passed: {record_count} records found")
    
    def get_clean_data(self):
        """Return cleaned data if validation passed"""
        if not self.validation_results["is_valid"]:
            logger.warning("Returning data with validation errors")
            
        # Clean data
        clean_data = self.data.copy()
        
        # Handle missing values
        clean_data = clean_data.fillna({
            "Title": "No title provided",
            "Change_Type": "unspecified",
            "Risk_Rating": "unspecified",
            "Requestor": "Unknown",
            "Approver": "Unknown",
            "Deployment_Method": "Unknown",
            "Status": "Unknown"
        })
        
        # Standardize values
        if "Risk_Rating" in clean_data.columns:
            # Map short codes to full values
            risk_mapping = {"H": "High", "M": "Medium", "L": "Low"}
            clean_data["Risk_Rating"] = clean_data["Risk_Rating"].replace(risk_mapping)
            
        if "Change_Type" in clean_data.columns:
            # Map short codes to full values
            type_mapping = {"app": "application", "infra": "infrastructure", "config": "configuration"}
            clean_data["Change_Type"] = clean_data["Change_Type"].replace(type_mapping)
        
        return clean_data 
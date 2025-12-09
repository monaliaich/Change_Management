import os
import logging
import pandas as pd
import hashlib
from concurrent.futures import ThreadPoolExecutor
import re
import json
import time
import traceback
import asyncio
from datetime import datetime as dt
from azure.ai.agents import AgentsClient
from azure.identity import AzureCliCredential
from utils.data_extractor import DataExtractor
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.environ['PYTHONHTTPSVERIFY'] = '0'

# Create a custom SSL context
import ssl
import certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class ApproverValidationAgent:
    """
    Agent responsible for validating approvers in change management processes.
    
    This agent performs the following tasks:
    1. Load verified population data
    2. Load IAM users data
    3. Validate approvers against IAM users list
    4. Check if approvers have the correct role
    5. Flag unauthorized approvers
    6. Generate a report with flagged records and reason codes
    """

    def __init__(self, data_dir="./data/input", output_data_dir="./data/output", 
             verified_population_file=None):
        
        self.name = "ApproverValidationAgent"
        self.logger = logging.getLogger(self.name)
        self.data_dir = data_dir
        self.output_data_dir = output_data_dir
        self.verified_population_file = verified_population_file
        self.parameters = {}
        self.metadata = {}
        
        # Data containers
        self.change_migration_data = None
        self.iam_users_data = None
        self.validation_results = None
    
        # Initialize the data extractor
        self.data_extractor = DataExtractor(data_dir, output_data_dir)
        
        # Validate required environment variables
        required = ["PROJECT_ENDPOINT", "AGENT_MODEL_DEPLOYMENT_NAME"]
        missing = [k for k in required if not os.environ.get(k)]
        if missing:
            self.logger.error("Missing env vars: %s", ", ".join(missing))
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

        # If validation passes, continue with setup
        self.PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT")
        self.AGENT_MODEL_DEPLOYMENT_NAME = os.environ.get("AGENT_MODEL_DEPLOYMENT_NAME")

        # Initialize Azure AI Foundry client
        try: 
            # Initialize Azure AI Foundry client with AzureCliCredential
            from azure.core.pipeline.transport import RequestsTransport
            transport = RequestsTransport(connection_verify=False)
            
            self.client = AgentsClient(
                endpoint=self.PROJECT_ENDPOINT,
                credential=AzureCliCredential(),
                transport=transport
            )   
            self.logger.info("Azure AI Foundry client initialized successfully")
        except Exception as e:
            # Added error handling for client initialization
            self.logger.error(f"Error initializing Azure AI Foundry client: {str(e)}")
            self.logger.warning("Continuing without Azure AI Foundry integration") 
            self.client = None

    def load_verified_population_data(self):
        """
        Load change migration population data from verified population file.
        """
        data, metadata, success = self.data_extractor.load_verified_population_data(self.verified_population_file)
        
        if success:
            self.change_migration_data = data
            self.metadata.update(metadata)
            return True
        return False

    def load_iam_users_data(self):
        """
        Load IAM users status data.
        """
        data, success = self.data_extractor.load_iam_users_data()
        
        if success:
            self.iam_users_data = data
            return True
        return False

    def validate_approvers_with_ai(self):
        """
        Use Azure AI Foundry to validate approvers against IAM users list.
        """
        try:
            self.logger.info("Validating approvers using Azure AI Foundry")
        
            # Check if required data is loaded
            if self.change_migration_data is None or self.iam_users_data is None:
                self.logger.error("Required data not loaded for approver validation")
                return False
            
            # Prepare data for AI analysis
            merged_data = self._prepare_data_for_validation()
            
            # Process data in batches and send to AI for analysis
            all_results = self._process_batches_with_ai(merged_data)
            
            # Process results
            self._process_ai_results(all_results, merged_data)

            return True

        except Exception as e:
            self.logger.error(f"Error validating approvers with AI: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False    

    def _prepare_data_for_validation(self):
        """
        Prepare data for approver validation.
        """
        # Create a copy of the change migration data with only essential columns
        validation_data = self.change_migration_data.copy()
        
        # Add IAM user IDs as a simple comma-separated string
        iam_user_ids = ','.join(self.iam_users_data['User_ID'].tolist())
        validation_data['IAM_User_IDs'] = iam_user_ids
        
        # Add IAM approver roles as a simple comma-separated string
        approver_roles = self.iam_users_data[self.iam_users_data['IAM_Role'] == 'Approver']
        approver_user_ids = ','.join(approver_roles['User_ID'].tolist())
        validation_data['IAM_Approver_IDs'] = approver_user_ids
        
        # Add IT/Business Manager information as a simple comma-separated string
        it_bu_managers = approver_roles[
            approver_roles['Mapped_DOA_Role'].str.contains('IT Manager|Business Manager', case=False, na=False)
        ]
        it_bu_manager_ids = ','.join(it_bu_managers['User_ID'].tolist())
        validation_data['IT_BU_Manager_IDs'] = it_bu_manager_ids

        return validation_data   
        
    def _process_batches_with_ai(self, data):
        """
        Process data in batches and send to AI for analysis.
        """
        all_results = []
    
        # Process changes in smaller batches
        batch_size = 10  # Smaller batch size for better reliability
        self.logger.info(f"Processing {len(data)} records in batches of {batch_size}")
        
        # Create batches
        batches = []
        for i in range(0, len(data), batch_size):
            batch = data.iloc[i:i+batch_size]
            batch_json = batch.to_json(orient='records')
            prompt = self._create_ai_prompt(batch_json)
            batches.append((prompt, i, batch_size, len(data)))

        self.logger.info(f"Processing batch {i//batch_size + 1}/{(len(data) + batch_size - 1)//batch_size}")
        
        # Process batches asynchronously
        batch_results = asyncio.run(self._process_batches_async(batches))

        # Flatten results
        self.logger.info(f"Received {len(batch_results)} batch results")
        for i, results in enumerate(batch_results):
            self.logger.info(f"Batch {i+1} returned {len(results) if results else 0} results")
            if results and len(results) > 0:
                self.logger.info(f"Sample result keys: {list(results[0].keys())}")

        # Flatten results
        for results in batch_results:
            if results:
                all_results.extend(results)   

        self.logger.info(f"Total results after processing: {len(all_results)}")
        return all_results      
    

    def _call_ai_for_analysis(self, prompt, batch_index, batch_size, total_records):
        """
        Call Azure AI Foundry for analysis synchronously.
        """
        try:
            self.logger.info(f"Sending batch {batch_index//batch_size + 1}/{(total_records + batch_size - 1)//batch_size} to Azure AI Foundry")
    
            # Check if Azure AI client is available
            if not hasattr(self, 'client'):
                self.logger.error("Azure AI Foundry client not properly initialized")
                raise AttributeError("Azure AI Foundry client not properly initialized")
            
            # Create the system prompt
            system_prompt = "You are an expert in IT audit, compliance, and segregation of duties analysis."

            # Call AI with thread and run
            return self._call_ai_with_thread_and_run(system_prompt, prompt)

        except Exception as e:
            self.logger.error(f"Error getting AI analysis for batch {batch_index//batch_size + 1}: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return []    
    
    async def _process_batches_async(self, batches):
        """
        Process batches asynchronously.
        """

        # Create tasks for each batch
        tasks = []
        for batch_data in batches:
            prompt, i, batch_size, total_records = batch_data
            task = asyncio.create_task(self._call_ai_for_analysis_async(prompt, i, batch_size, total_records))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
        # Process results, handling any exceptions
        processed_results = []    

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Error processing batch {i}: {str(result)}")
                # Return empty list for this batch
                processed_results.append([])
            else:
                processed_results.append(result)
        return processed_results        
    
    
    def _create_ai_prompt(self, batch_json):
        """
        Create the prompt for the AI model.
        """
        return f"""
            You are validating approvers in a change management system. Here are the records to analyze:
            {batch_json}

            For each record, determine if the approver is authorized by checking:

            For each record, follow these exact steps:
            1. Get the Approver_ID from the record
            2. Check if Approver_ID is in IAM_User_IDs list
                - If NOT found: Status="Exception", Reason_Code="Unauthorized Approver - User not found in IAM"
                - If found: Continue to step 3
        
            3. Check if Approver_ID is in IAM_Approver_IDs list
                - If NOT found: Status="Exception", Reason_Code="Unauthorized Approver - User does not have approver role"
                - If found: Continue to step 4
        
            4. Check if Approver_ID is in IT_BU_Manager_IDs list
                - If NOT found: Status="Exception", Reason_Code="Unauthorized Approver - Not IT/Business Manager"
                - If found: Status="OK", Reason_Code="Valid approver"

            REQUIRED OUTPUT FORMAT:
            A JSON array containing one object for each input record, with these exact fields:
            - Change_ID: The ID from the record
            - Status: Either "OK" or "Exception"
            - Reason_Code: The reason based on the validation steps

            EXAMPLE OUTPUT:
            [
                {{"Change_ID": "CHG1000", "Status": "Exception", "Reason_Code": "Unauthorized Approver - User not found in IAM"}},
                {{"Change_ID": "CHG1001", "Status": "OK", "Reason_Code": "Valid approver"}}
            ]

            CRITICAL: You MUST analyze EVERY record in the input data. Do not skip any records.
            Return ONLY the JSON array with no additional text.
            """

    async def _call_ai_for_analysis_async(self, prompt, batch_index, batch_size, total_records):
        """
        Call Azure AI Foundry for analysis asynchronously.
        """
        try:
            self.logger.info(f"Sending batch {batch_index//batch_size + 1}/{(total_records + batch_size - 1)//batch_size} to Azure AI Foundry")
        
            # Check if Azure AI client is available
            if not hasattr(self, 'client'):
                self.logger.error("Azure AI Foundry client not properly initialized")
                raise AttributeError("Azure AI Foundry client not properly initialized")
            
            # Create the system prompt
            system_prompt = """You are an expert IT audit assistant specializing in compliance and user authorization validation. 
            Your task is to analyze change management records and validate if approvers have proper authorization."""
        
            # Use ThreadPoolExecutor to run synchronous API calls in a separate thread
            with ThreadPoolExecutor() as executor:
                future = executor.submit(
                    self._call_ai_with_thread_and_run,
                    system_prompt,
                    prompt,
                    max_retries=5
                )
                return await asyncio.wrap_future(future)

        except Exception as e:
            self.logger.error(f"Error getting AI analysis for batch {batch_index//batch_size + 1}: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _call_ai_with_thread_and_run(self, system_prompt, user_prompt, max_retries=3):
        """
        Call AI using the thread and run API pattern.
        """
        retry_count = 0
        while retry_count < max_retries:
            try:

                # First create a thread
                thread_response = self.client.threads.create()
                thread_id = thread_response.id
                self.logger.info(f"Created thread with ID: {thread_id}")

                # Add system instructions as a user message
                system_instructions = f"You are an expert in IT audit, compliance, and user authorization validation. {system_prompt}"

                # Add user message with combined instructions and prompt
                self.client.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=f"{system_instructions}\n\n{user_prompt}"
                )    

                # Try to get an agent ID using the helper method
                agent_id = self._get_agent_id()

                # Create a run
                if agent_id:
                    # Try with agent_id
                    self.logger.info(f"Creating run with agent_id: {agent_id}")
                    run_response = self.client.runs.create(
                        thread_id=thread_id,
                        agent_id=agent_id
                    )
                    
                else:    
                    # Try with model name directly
                    self.logger.info(f"Creating run with model: {self.AGENT_MODEL_DEPLOYMENT_NAME}")
                    run_response = self.client.runs.create(
                        thread_id=thread_id,
                        model=self.AGENT_MODEL_DEPLOYMENT_NAME
                    ) 
                run_id = run_response.id
                self.logger.info(f"Created run with ID: {run_id}")

                # Poll for completion
                result = self._poll_for_completion(thread_id, run_id) 
                if result:
                    return result                 
            
                # If we got here, polling failed but didn't raise an exception
                self.logger.warning(f"Polling completed but no results returned. Retry {retry_count + 1}/{max_retries}")
                retry_count += 1
              
            except Exception as e:
                self.logger.error(f"Error using create_thread_and_run (attempt {retry_count + 1}/{max_retries}): {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    self.logger.info(f"Retrying in 2 seconds...")
                    time.sleep(2)  # Wait before retrying
        # If all retries fail, try the alternative methods as a last resort
        self.logger.error(f"Failed after {max_retries} attempts")
        return []
        

    def _call_ai_with_alternative_methods(self, system_prompt, user_prompt, max_retries=3):
        """
        Call AI using alternative API methods with retries.
        """
        retry_count = 0
        while retry_count < max_retries:
            try:
                response = None

                if self.client is None:
                    self.logger.error("Azure AI client not available")
                    return []

                if hasattr(self.client, 'chat') and hasattr(self.client.chat, 'completions'):
                    # OpenAI-style pattern
                    response = self.client.chat.completions.create(
                        model=self.AGENT_MODEL_DEPLOYMENT_NAME,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.3,
                    )
                    self.logger.info("Used chat.completions.create API pattern")
                elif hasattr(self.client, 'completions'):
                    # Direct completions pattern
                    response = self.client.completions.create(
                        model=self.AGENT_MODEL_DEPLOYMENT_NAME,
                        prompt=f"{system_prompt}\n\n{user_prompt}",
                        temperature=0.3,
                    )
                    self.logger.info("Used completions.create API pattern") 
                elif hasattr(self.client, 'agents') and hasattr(self.client.agents, 'run'):
                    # Agents run pattern
                    response = self.client.agents.run(
                        deployment_name=self.AGENT_MODEL_DEPLOYMENT_NAME,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    self.logger.info("Used agents.run API pattern")
                elif hasattr(self.client, 'run'):
                    self.logger.info("Trying direct run API pattern")
                    response = self.client.run(
                        model=self.AGENT_MODEL_DEPLOYMENT_NAME,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    self.logger.info("Used direct run API pattern") 
                else:
                    self.logger.error("No compatible API methods found")
                    return []       
                """else:
                    # Try a direct invoke pattern
                    response = self.client.invoke(
                        deployment_name=self.AGENT_MODEL_DEPLOYMENT_NAME,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.3,
                        response_format={"type": "json_object"}
                    )
                    self.logger.info("Used direct invoke API pattern")"""
                 
                # Extract text from response
                ai_response_text = self._extract_text_from_response(response) 

                if ai_response_text:
                    # Try to parse the AI response as JSON
                    try:
                        ai_response = json.loads(ai_response_text) 
                        # Extract results from the response
                        if isinstance(ai_response, list):
                            return ai_response
                        elif isinstance(ai_response, dict):
                            if 'results' in ai_response:
                                return ai_response['results']
                            else:
                                return [ai_response]
                        else:
                            self.logger.warning(f"Unexpected response format: {type(ai_response)}")
                            return [] 
                    except json.JSONDecodeError:
                        # Try to extract JSON from the text
                        self.logger.warning("Failed to parse response as JSON, trying to extract JSON")
                        json_match = re.search(r'\[\s*{[\s\S]*?}\s*\]', ai_response_text)
                        if json_match:
                            try:
                                extracted_json = json.loads(json_match.group(0))
                                self.logger.info("Successfully extracted JSON array from response")
                                return extracted_json
                            except json.JSONDecodeError:
                                self.logger.error("Failed to parse extracted JSON") 
                        # If we still don't have valid JSON, retry
                        retry_count += 1
                        if retry_count < max_retries:
                            self.logger.info(f"Retrying in 2 seconds...")
                            time.sleep(2)
                        continue                
                else:
                    self.logger.error("Could not extract text content from AI response")
                    retry_count += 1
                    if retry_count < max_retries:
                        self.logger.info(f"Retrying in 2 seconds...")
                        time.sleep(2)
                    continue      
            except Exception as e:
                self.logger.error(f"Error using alternative API methods (attempt {retry_count + 1}/{max_retries}): {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    self.logger.info(f"Retrying in 2 seconds...")
                    time.sleep(2)           

        self.logger.error(f"Failed after {max_retries} attempts")
        return []            
    
    
    def _extract_text_from_response(self, response):
        """
        Extract text from the response.
        """
        try:
            if hasattr(response, 'choices') and len(response.choices) > 0:
                if hasattr(response.choices[0], 'message') and hasattr(response.choices[0].message, 'content'):
                    return response.choices[0].message.content
                elif hasattr(response.choices[0], 'text'):
                    return response.choices[0].text
            elif hasattr(response, 'output'):
                return response.output
            elif hasattr(response, 'content'):
                return response.content
            elif isinstance(response, dict) and 'content' in response:
                return response['content']
            elif isinstance(response, str):
                return response 
            
            return None   
        except Exception as e:
            self.logger.error(f"Error extracting text from response: {str(e)}")
            return None        
    
    def _get_agent_id(self):
        """
        Get an agent ID for the AI analysis.
        """
        try:
            # Try to list available agents
            agents_list = list(self.client.list_agents())
            self.logger.info(f"Available agents: {[a.id for a in agents_list]}")

            # If no agents are found, create one
            if not agents_list:
                self.logger.info("No agents found. Creating a new agent.")
                agent = self.client.create_agent(
                    name="Approver Validation Agent",
                    description="Validates approvers in change management processes",
                    model=self.AGENT_MODEL_DEPLOYMENT_NAME
                )
                return agent.id
            else:
                # Use the first available agent
                return agents_list[0].id

        except Exception as e:
            self.logger.error(f"Error getting agent ID: {str(e)}")
            return None    


    def _poll_for_completion(self, thread_id, run_id, max_retries=30, retry_interval=2):
        """
        Poll for completion of the AI run.
        """
        retry_count = 0

        while retry_count < max_retries:
            try:
                run_status = self.client.runs.get(thread_id=thread_id, run_id=run_id)
                self.logger.info(f"Run status: {run_status.status}")

                if run_status.status == "completed":
                    # Get the messages from the thread
                    messages = self.client.messages.list(thread_id=thread_id)
                
                    # Get the last assistant message
                    assistant_messages = [msg for msg in messages if msg.role == "assistant"]

                    if assistant_messages:
                        # Extract and process the AI response
                        return self._extract_ai_response(assistant_messages[-1])
                    else:
                        self.logger.warning("No assistant messages found in the thread")
                        return []               
                elif run_status.status in ["failed", "cancelled", "expired"]:
                    self.logger.error(f"Run failed with status: {run_status.status}")
                    return []               
                # Wait before checking again
                time.sleep(retry_interval)
                retry_count += 1    
            except Exception as e:
                self.logger.error(f"Error polling for completion: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(retry_interval)    
        self.logger.error(f"Run timed out after {max_retries * retry_interval} seconds")
        return []   

    def _extract_ai_response(self, message):
        """
        Extract the AI response from the message.
        """
        try: 
            # Try to extract the text content
            ai_response_text = None

            # Check if content is available
            if hasattr(message, 'content'):
                content = message.content

                # If content is a list
                if isinstance(content, list):
                    for item in content:
                        if hasattr(item, 'text'):
                            text = item.text
                            if isinstance(text, str):
                                ai_response_text = text
                            elif hasattr(text, 'value'):
                                ai_response_text = text.value
                            else:
                                ai_response_text = str(text)

                # If content is a string
                elif isinstance(content, str):
                    ai_response_text = content 
                # If content has a text attribute
                elif hasattr(content, 'text'):
                    ai_response_text = content.text    

            # If we still don't have text, try other attributes
            if not ai_response_text and hasattr(message, 'text_messages') and message.text_messages:
                ai_response_text = message.text_messages[0]
            elif not ai_response_text and hasattr(message, 'text'):
                ai_response_text = message.text   
            
            if not ai_response_text:
                self.logger.error("Could not extract text from message")
                return []  
            
            # Use the improved JSON extraction method
            return self._extract_json_from_text(ai_response_text)            

        except Exception as e:
            self.logger.error(f"Error extracting AI response: {str(e)}")
            return []    

    def _extract_json_from_text(self, text):
        """
        Extract JSON from the text.
        """
        try:
            # First, clean up the text to handle common formatting issues
            # Remove any markdown code block markers
            text = re.sub(r'```(?:json)?\s*|\s*```', '', text)

            # Look for JSON content between triple backticks
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
            if json_match:
                json_content = json_match.group(0)
                self.logger.info(f"Found JSON array")   
            else:
                # Try to find any array in square brackets
                json_match = re.search(r'\[\s*{[\s\S]*?}\s*\]', text) 
                if json_match:
                    json_content = json_match.group(0)
                    self.logger.info(f"Found JSON array")
                else:
                    # Try to find any object in curly braces
                    json_match = re.search(r'{[\s\S]*?}', text)
                    if json_match:  
                        json_content = json_match.group(0)
                        self.logger.info(f"Found JSON object")
                    else:
                        # Try to parse the entire text as JSON  
                        try:
                            json.loads(text)
                            json_content = text
                            self.logger.info("Using entire text as JSON")
                        except:
                            # Create a simple JSON structure with the text
                            self.logger.error("Could not find JSON content in the response")
                            return []          

            # Parse the JSON content
            try:
                ai_response = json.loads(json_content)
                self.logger.info(f"Parsed JSON: {type(ai_response)}") 
            
                # Process the response based on its structure
                if isinstance(ai_response, list):
                    return ai_response
                elif isinstance(ai_response, dict):
                    if 'results' in ai_response:
                        return ai_response['results']
                    else:
                        return [ai_response]
                else:
                    self.logger.warning(f"Unexpected JSON structure: {type(ai_response)}")
                    return []

            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing JSON: {str(e)}")
                return []      
        except Exception as e:
            self.logger.error(f"Error extracting JSON from text: {str(e)}")
            return []    

    
    def _process_ai_results(self, all_results, original_data):
        """
        Process AI results and create the validation results dataframe.
        """
        try:
            self.logger.info(f"Processing AI results: {len(all_results)} records")
            # Check if results are empty
            if not all_results:
                self.logger.warning("No results returned from AI analysis")
                # Create a default dataframe with all records marked as "Unknown"
                validation_df = original_data.copy()
                # Remove reference columns
                columns_to_remove = ['IAM_User_IDs', 'IAM_Approver_IDs', 'IT_BU_Manager_IDs', 'IAM_Data']
                validation_df = validation_df.drop(columns=[col for col in columns_to_remove if col in validation_df.columns])
                validation_df['Status'] = "Unknown"
                validation_df['Reason_Code'] = "AI analysis failed"
                self.validation_results = validation_df
                return
        
            # Convert AI results to DataFrame
            results_df = pd.DataFrame(all_results)
            self.logger.info(f"Columns in AI results: {results_df.columns.tolist()}")
        
            # Determine which columns to use based on what's available
            change_id_col = None
            status_col = None
            reason_code_col = None
        
            # Check for Change_ID column (case-insensitive)
            for col in results_df.columns:
                if col.lower() == 'change_id':
                    change_id_col = col
                    break
            # Check for Status column (case-insensitive)
            for col in results_df.columns:
                if col.lower() == 'status':
                    status_col = col
                    break
        
            # Check for Reason_Code column (case-insensitive)
            for col in results_df.columns:
                if col.lower() == 'reason_code':
                    reason_code_col = col
                    break

            # If any column is missing, log an error and create a default dataframe
            if not change_id_col or not status_col or not reason_code_col:
                self.logger.error(f"Missing required columns in AI results. Available columns: {results_df.columns.tolist()}")
                validation_df = original_data.copy()
                # Remove reference columns
                columns_to_remove = ['IAM_User_IDs', 'IAM_Approver_IDs', 'IT_BU_Manager_IDs', 'IAM_Data']
                validation_df = validation_df.drop(columns=[col for col in columns_to_remove if col in validation_df.columns])
                validation_df['Status'] = "Unknown"
                validation_df['Reason_Code'] = "AI results missing required columns"
                self.validation_results = validation_df
                return
        
            # Remove the reference columns we added for AI analysis
            columns_to_remove = ['IAM_User_IDs', 'IAM_Approver_IDs', 'IT_BU_Manager_IDs', 'IAM_Data']
            original_data_clean = original_data.drop(columns=[col for col in columns_to_remove if col in original_data.columns])
            
            # Merge AI results with original data to get complete records
            # First, remove the IAM reference columns we added for AI analysis
            """if 'IAM_User_IDs' in original_data.columns:
                original_data = original_data.drop(columns=['IAM_User_IDs'])
            if 'IAM_Approver_IDs' in original_data.columns:
                original_data = original_data.drop(columns=['IAM_Approver_IDs'])"""
        
            # Merge on Change_ID
            validation_df = pd.merge(
                original_data_clean,
                results_df[[change_id_col, status_col, reason_code_col]],
                left_on='Change_ID',
                right_on=change_id_col,
                how='left'
            )

            # Drop the duplicate change_id column
            if change_id_col in validation_df.columns and change_id_col != 'Change_ID':
                validation_df = validation_df.drop(columns=[change_id_col])
        
            # Rename columns to standardized names if needed
            if status_col != 'Status':
                validation_df = validation_df.rename(columns={status_col: 'Status'})
            if reason_code_col != 'Reason_Code':
                validation_df = validation_df.rename(columns={reason_code_col: 'Reason_Code'})

            # Fill missing values for records that weren't analyzed
            validation_df['Status'] = validation_df['Status'].fillna("Unknown")
            validation_df['Reason_Code'] = validation_df['Reason_Code'].fillna("Record not analyzed")

        
            self.validation_results = validation_df
            self.logger.info(f"Processed {len(validation_df)} records")
            self.logger.info(f"Exception records: {len(validation_df[validation_df['Status'] == 'Exception'])}")
            self.logger.info(f"OK records: {len(validation_df[validation_df['Status'] == 'OK'])}")
        
        except Exception as e:
            self.logger.error(f"Error processing AI results: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        
            # Create a default dataframe with all records marked as "Unknown"
            validation_df = original_data.copy()
            # Remove reference columns
            columns_to_remove = ['IAM_User_IDs', 'IAM_Approver_IDs', 'IT_BU_Manager_IDs', 'IAM_Data']
            validation_df = validation_df.drop(columns=[col for col in columns_to_remove if col in validation_df.columns])
            validation_df['Status'] = "Unknown"
            validation_df['Reason_Code'] = f"Error processing results: {str(e)}"
            self.validation_results = validation_df


    def save_validation_report(self):
        """
        Save the approver validation report.
        """
        try:
            self.logger.info("Saving approver validation report")
    
            # Check if we have results to save
            if self.validation_results is None:
                self.logger.error("No validation results to save")
                return False
    
            # Create output directory if it doesn't exist
            output_dir = os.path.join(self.output_data_dir, "approver_validations")
            os.makedirs(output_dir, exist_ok=True)
    
            # Generate filename
            filename = "approver_validation_report.xlsx"
            output_path = os.path.join(output_dir, filename)

            # Prepare metadata for the report
            report_metadata = {
                'report_timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S'),
                'generated_by': 'ApproverValidationAgent',
                'source_population_file': os.path.basename(self.verified_population_file) if self.verified_population_file else 'Unknown',
                'total_records_analyzed': len(self.validation_results),
                'exception_records': len(self.validation_results[self.validation_results['Status'] == 'Exception']) if 'Status' in self.validation_results.columns else 0, 
                'ok_records': len(self.validation_results[self.validation_results['Status'] == 'OK']) if 'Status' in self.validation_results.columns else 0, 
                'unknown_records': len(self.validation_results[self.validation_results['Status'] == 'Unknown']) if 'Status' in self.validation_results.columns else len(self.validation_results), 
                'environment': 'Development'
            }
    
            # Create Excel writer
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Write validation results to sheet1
                self.validation_results.to_excel(writer, sheet_name='Validation Results', index=False)
        
                # Write metadata to sheet2
                metadata_df = pd.DataFrame(list(report_metadata.items()), columns=['Key', 'Value'])
                metadata_df.to_excel(writer, sheet_name='Report Metadata', index=False)
    
                self.logger.info(f"Approver validation report saved to {output_path}")
                return output_path
        
        except Exception as e:
            self.logger.error(f"Error saving approver validation report: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def run(self):
        """
        Run the complete approver validation workflow.
        """
        try:
            self.logger.info("Starting ApproverValidationAgent")
        
            # Step 1: Load verified population data
            success = self.load_verified_population_data()
            if not success:
                self.logger.error("Failed to load verified population data")
                return False
        
            # Step 2: Load IAM users data
            success = self.load_iam_users_data()
            if not success:
                self.logger.error("Failed to load IAM users data")
                return False
        
            # Step 3: Validate approvers with AI - use await here
            success = self.validate_approvers_with_ai()
            if not success:
                self.logger.error("Failed to validate approvers with AI")
                return False
        
            # Step 4: Save validation report
            output_file = self.save_validation_report()
            if not output_file:
                self.logger.error("Failed to save validation report")
                return False
        
            self.logger.info(f"ApproverValidationAgent completed successfully. Output file: {output_file}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error running ApproverValidationAgent: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False        
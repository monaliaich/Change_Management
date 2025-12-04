from operator import index
import os
import ssl
import certifi
import logging
import pandas as pd
import hashlib
import json
import time
import re
import traceback
from datetime import datetime as dt
from azure.ai.agents import AgentsClient
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
#from azure.identity import DefaultAzureCredential
from azure.identity import AzureCliCredential
from config.settings import DATA_INPUT_PATH, DATA_OUTPUT_PATH

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.environ['PYTHONHTTPSVERIFY'] = '0'

# Create a custom SSL context
ssl_context = ssl.create_default_context(cafile=certifi.where())
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Initialize Azure AI Foundry client with AzureCliCredential and custom transport
from azure.core.pipeline.transport import RequestsTransport
transport = RequestsTransport(connection_verify=False)



class SODViolationDetectionAgent:
    """
    Agent responsible for detecting Segregation of Duties (SOD) violations in change management processes.
    
    This agent performs the following tasks:
    1. Load change migration population data from verified population file
    2. Load approval workflow data
    3. Load deployment log data
    4. Load DOA matrix data
    5. Identify SOD violations by comparing roles
    6. Generate violation report with detailed reasons
    7. Save the violation report with metadata
    """

    def __init__(self, data_dir="./data/input", output_data_dir="./data/output", 
                 verified_population_file=None):
        
        self.name = "SODViolationDetectionAgent"
        self.logger = logging.getLogger(self.name)
        self.data_dir = data_dir
        self.output_data_dir = output_data_dir
        self.verified_population_file = verified_population_file
        self.parameters = {}
        self.metadata = {}
        
        # Data containers
        self.change_migration_data = None
        self.approval_workflow_data = None
        self.deployment_log_data = None
        self.doa_matrix_data = None
        self.violations_data = None
        
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
        

    def detect_sod_violations_with_ai(self):
        """
        Use Azure AI Foundry to detect and analyze SOD violations.
        """

        try:
            self.logger.info("Detecting SOD violations using Azure AI Foundry")
        
            # Step 1: Prepare merged data
            merged_df = self._prepare_merged_data()
            if merged_df.empty:
                self.logger.warning("No data available for SOD violation detection")
                self.violations_data = pd.DataFrame()
                return True
            
            # Step 2: Process data in batches and send to AI for analysis
            all_results = self._process_batches_with_ai(merged_df)
            
            # Step 3: Process results and handle missing records
            self._process_ai_results(all_results, merged_df)

            return True

        except Exception as e:
            self.logger.error(f"Error detecting SOD violations with AI: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False    
    
    
    def _prepare_merged_data(self):
        """
        Prepare merged data from all data sources for SOD analysis.
        """
        # Ensure all required data is loaded
        if any(data is None for data in [
            self.change_migration_data,  
            self.deployment_log_data,
            self.iam_users_data,
            self.doa_matrix_data
        ]):
            self.logger.error("Required data not loaded for SOD violation detection")
            return pd.DataFrame()
        
        # Log column names for debugging
        self.logger.info(f"Change migration data columns: {self.change_migration_data.columns.tolist()}")
        self.logger.info(f"CI/CD deployment logs columns: {self.deployment_log_data.columns.tolist()}")
        self.logger.info(f"IAM users data columns: {self.iam_users_data.columns.tolist()}")
        self.logger.info(f"DOA matrix data columns: {self.doa_matrix_data.columns.tolist()}")

        merged_data = []
    
        # Process each change in the change migration data
        for _, change_row in self.change_migration_data.iterrows():
            try:
                # Check if required columns exist in this row
                if 'Change_ID' not in change_row or 'Asset_Name' not in change_row:
                    self.logger.warning(f"Missing required columns in row, skipping")
                    continue

                change_id = change_row['Change_ID']
                asset_name = change_row['Asset_Name']

                # Get requestor info from change migration data
                requestor_id = change_row.get('Requestor_ID', 'Unknown')
                requestor_name = change_row.get('Requestor_Name', 'Unknown')
                developer_id = change_row.get('Developer_ID', 'Unknown')
                developer_name = change_row.get('Developer_Name', 'Unknown')
                approver_id = change_row.get('Approver_ID', 'Unknown')
                approver_name = change_row.get('Approver_Name', 'Unknown')

                # Find corresponding deployment log data
                deployment_rows = self.deployment_log_data[
                    (self.deployment_log_data['Linked_Change_ID'] == change_id) & 
                    (self.deployment_log_data['Asset_Name'] == asset_name)
                ]

                # Skip if we don't have matching deployment records
                if len(deployment_rows) == 0:
                    self.logger.warning(f"No deployment logs found for Change_ID: {change_id}, Asset_Name: {asset_name}")
                    continue

                # Get deployer info from CI/CD deployment logs
                deployer_id = deployment_rows.iloc[0]['Deployer_ID']
                deployer_name = deployment_rows.iloc[0]['Deployer_Name']

                # Get IAM roles for each person
                requestor_role = self._get_iam_role(requestor_id)
                approver_role = self._get_iam_role(approver_id)
                developer_role = self._get_iam_role(developer_id)
                deployer_role = self._get_iam_role(deployer_id)


                # Create change info dictionary
                change_info = {
                    'Change_ID': change_id,
                    'Asset_Name': asset_name,
                    'Change_Type': change_row.get('Change_Type', 'Unknown'),
                    'Risk_Rating': change_row.get('Risk_Rating', 'Unknown'),
                    'Requestor_ID': requestor_id,
                    'Requestor_Name': requestor_name,
                    'Requestor_Role': requestor_role,
                    'Approver_ID': approver_id,
                    'Approver_Name': approver_name,
                    'Approver_Role': approver_role,
                    'Developer_ID': developer_id,
                    'Developer_Name': developer_name,
                    'Developer_Role': developer_role,
                    'Deployer_ID': deployer_id,
                    'Deployer_Name': deployer_name,
                    'Deployer_Role': deployer_role,
                    'Deployment_ID': deployment_rows.iloc[0]['Deployment_ID']
                }
            
                merged_data.append(change_info)

            except Exception as e:
                self.logger.error(f"Error processing row: {str(e)}")
                continue    
        # Convert to DataFrame
        return pd.DataFrame(merged_data)    
    
    def _get_iam_role(self, user_id):
        """
        Get IAM role for a user ID.
        """
        user_iam = self.iam_users_data[self.iam_users_data['User_ID'] == user_id]
        if len(user_iam) > 0:
            return user_iam.iloc[0]['Mapped_DOA_Role']
        return "Unknown"


    def _process_batches_with_ai(self, merged_df):
        """
        Process data in batches and send to AI for analysis.
        """
        # Initialize all_results list
        all_results = []
        # Process changes in batches to avoid overwhelming the AI service
        batch_size = 10  # Increased from 5 to 10 for better efficiency
        self.logger.info(f"Processing {len(merged_df)} records in batches of {batch_size}")

        # Create batches
        batches = []
        for i in range(0, len(merged_df), batch_size):
            batch = merged_df.iloc[i:i+batch_size]
            batch_json = batch.to_json(orient='records')
            prompt = self._create_ai_prompt(batch_json)
            batches.append((prompt, i, batch_size, len(merged_df)))

        # Process batches asynchronously
        batch_results = asyncio.run(self._process_batches_async(batches))

         # Flatten results
        for results in batch_results:
            if results:
                all_results.extend(results)   

        return all_results         

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
            system_prompt = "You are an expert in IT audit, compliance, and segregation of duties analysis."
        
            # Use ThreadPoolExecutor to run synchronous API calls in a separate thread
            with ThreadPoolExecutor() as executor:
                if hasattr(self.client, 'create_thread_and_run'):
                    # Run the synchronous method in a separate thread to avoid blocking
                    future = executor.submit(
                        self._call_ai_with_thread_and_run,
                        system_prompt,
                        prompt
                    )
                    return await asyncio.wrap_future(future)
                else:
                    future = executor.submit(
                        self._call_ai_with_alternative_methods,
                        system_prompt,
                        prompt
                    )
                    return await asyncio.wrap_future(future)

        except Exception as e:
            self.logger.error(f"Error getting AI analysis for batch {batch_index//batch_size + 1}: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return []


    def _create_ai_prompt(self, batch_json):
        """
        Create the prompt for the AI model.
        """

        return f"""
            Analyze the following change management records for Segregation of Duties (SOD) violations:

            {batch_json}

            For each record, determine if there are any SOD violations by checking if the same person 
            (identified by ID) is performing multiple roles:

            1. Requestor
            2. Developer
            3. Approver
            4. Deployer

            SOD principles require that these roles should be performed by different individuals.

            IDEAL SCENARIO: For a single Change_ID and Asset_Name, the Requestor_ID, Approver_ID, Developer_ID, and Deployer_ID should all be different.

            VIOLATION SCENARIOS:
            - If any two or more roles have the same ID, this is a violation
            - If all four roles have the same ID, this is a high-risk violation

            For each violation found, provide:
            1. Change_ID 
            2. Asset_Name
            3. Requestor_Id
            4. Requestor_Name
            5. Developer_Id
            6. Developer_Name
            7. Deployer_Id
            8. Deployer_Name
            9. Approval_Id
            10. Approval_Name
            11. Status: "OK" if no violations, "Exception" if any violations
            12. Exception_Reason: Format MUST be exactly like this example: "Role1 and Role2 share the same ID (UserID)"

            For each violation found, format the exception_reason field EXACTLY as follows:
            - For each role pair that shares the same ID, include: "[Role1] and [Role2] share the same ID ([ID])"
            - Separate multiple violations with semicolons
            Example: "Requestor and Developer share the same ID (USR001); Developer and Approver share the same ID (USR001)"

            Return your analysis as a JSON array of violation objects, with each object containing:
            - change_id
            - asset_name
            - requestor_id
            - requestor_name
            - developer_id
            - developer_name
            - deployer_id
            - deployer_name
            - approval_id
            - approval_name
            - status
            - exception_reason

            Include ALL records in your response, both those with violations and those without.

            IMPORTANT: You must return ALL records that were provided to you, with no omissions.
            If there are multiple records, make sure to include every single one in your response.
        """
    
    def _call_ai_for_analysis(self, prompt, batch_index, batch_size, total_records):
        """
        Call Azure AI Foundry for analysis.
        """
        try:
            self.logger.info(f"Sending batch {batch_index//batch_size + 1}/{(total_records + batch_size - 1)//batch_size} to Azure AI Foundry")
        
            # Check if Azure AI client is available
            if not hasattr(self, 'client'):
                self.logger.error("Azure AI Foundry client not properly initialized")
                raise AttributeError("Azure AI Foundry client not properly initialized")
            
            # Create the system prompt
            system_prompt = "You are an expert in IT audit, compliance, and segregation of duties analysis."

            # Try different API patterns
            if hasattr(self.client, 'create_thread_and_run'):
                return self._call_ai_with_thread_and_run(system_prompt, prompt)
            else:
                return self._call_ai_with_alternative_methods(system_prompt, prompt)
            
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
                system_instructions = f"You are an expert in IT audit, compliance, and segregation of duties analysis. {system_prompt}"

                # Add user message with combined instructions and prompt
                self.client.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=f"{system_instructions}\n\n{user_prompt}"
                )

                # Try to get an agent ID
                agent_id = self._get_agent_id()

                # Create a run
                if agent_id:
                    run_response = self.client.runs.create(
                        thread_id=thread_id,
                        agent_id=agent_id
                    )
                else:
                    # Try with model name directly
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
        self.logger.error(f"Failed after {max_retries} attempts")
        return []   


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
                    name="SOD Violation Detector",
                    description="Detects Segregation of Duties violations in change management processes",
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
            ai_response_text = self._extract_text_from_message(message)
            if ai_response_text:
                # Try to extract JSON from the text
                return self._extract_json_from_text(ai_response_text)
            else:
                self.logger.error("Could not extract text from message")
                return []

        except Exception as e:
            self.logger.error(f"Error extracting AI response: {str(e)}")
            return []    


    def _extract_text_from_message(self, message):
        """
        Extract text from the message.
        """
        try:
            # Check if content is available
            if hasattr(message, 'content'):
                content = message.content

                # If content is a list
                if isinstance(content, list):
                    for item in content:
                        if hasattr(item, 'text'):
                            text = item.text
                            if isinstance(text, str):
                                return text
                            elif hasattr(text, 'value'):
                                return text.value
                            else:
                                return str(text)
                # If content is a string
                elif isinstance(content, str):
                    return content 
                # If content has a text attribute
                elif hasattr(content, 'text'):
                    return content.text       
            # If we still don't have text, try other attributes
            if hasattr(message, 'text_messages') and message.text_messages:
                return message.text_messages[0]
            elif hasattr(message, 'text'):
                return message.text
            
            return None            
        except Exception as e:
            self.logger.error(f"Error extracting text from message: {str(e)}")
            return None


    def _extract_json_from_text(self, text):
        """
        Extract JSON from the text.
        """
        try:
            # Look for JSON content between triple backticks
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
            if json_match:
                json_content = json_match.group(1)
                self.logger.info(f"Found JSON content in backticks: {json_content[:100]}...")
            else:
                # Try to find any array in square brackets
                json_match = re.search(r'\[\s*{[\s\S]*?}\s*\]', text)
                if json_match:
                    json_content = json_match.group(0)
                    self.logger.info(f"Found JSON array: {json_content[:100]}...")
                else:
                    # Try to find any object in curly braces
                    json_match = re.search(r'{[\s\S]*?}', text)
                    if json_match:
                        json_content = json_match.group(0)
                        self.logger.info(f"Found JSON object: {json_content[:100]}...")  
                    else:
                        # Try to parse the entire text as JSON 
                        try:
                            json.loads(text)
                            json_content = text
                            self.logger.info("Using entire text as JSON")
                        except:
                            # Create a simple JSON structure with the text
                            self.logger.error("Could not find JSON content in the response")
                            self.logger.info("Creating a simple JSON structure with the text")  

                            # Extract information from the text using regex
                            change_id_match = re.search(r'Change_ID: ([A-Za-z0-9]+)', text)
                            asset_name_match = re.search(r'Asset_Name: ([A-Za-z0-9 ]+)', text)
                            status_match = re.search(r'Status: "([A-Za-z]+)"', text)
                        
                            change_id = change_id_match.group(1) if change_id_match else "Unknown"
                            asset_name = asset_name_match.group(1) if asset_name_match else "Unknown"
                            status = status_match.group(1) if status_match else "Unknown" 

                            # Create a simple JSON structure
                            json_content = json.dumps([{
                                "change_id": change_id,
                                "asset_name": asset_name,
                                "status": status,
                                "exception_reason": text
                            }])     

            # Parse the JSON content
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
        except Exception as e:
            self.logger.error(f"Error extracting JSON from text: {str(e)}")
            return []


    def _call_ai_with_alternative_methods(self, system_prompt, user_prompt, max_retries=3):
        """
        Call AI using alternative API methods with retries.
        """
        retry_count = 0
        while retry_count < max_retries:
            try:
                response = None

                if hasattr(self.client, 'chat') and hasattr(self.client.chat, 'completions'):
                    # OpenAI-style pattern
                    response = self.client.chat.completions.create(
                        model=self.AGENT_MODEL_DEPLOYMENT_NAME,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.3,
                        response_format={"type": "json_object"}
                    )
                    self.logger.info("Used chat.completions.create API pattern")
                elif hasattr(self.client, 'completions'):
                    # Direct completions pattern
                    response = self.client.completions.create(
                        model=self.AGENT_MODEL_DEPLOYMENT_NAME,
                        prompt=f"{system_prompt}\n\n{user_prompt}",
                        temperature=0.3,
                        response_format="json"
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
                else:
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
                    self.logger.info("Used direct invoke API pattern") 
                
                # Extract text from response
                ai_response_text = self._extract_text_from_response(response)          

                if ai_response_text:
                    # Parse the AI response 
                    ai_response = json.loads(ai_response_text) 
                    # Extract results from the response
                    if 'results' in ai_response and isinstance(ai_response['results'], list):
                        return ai_response['results']
                    elif isinstance(ai_response, list):
                        return ai_response
                    elif isinstance(ai_response, dict):
                        return [ai_response]
                    else:
                        self.logger.warning(f"Unexpected response format from AI: {ai_response}")
                        # Try next retry instead of returning empty list
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

    def _process_ai_results(self, all_results, merged_df):
        """
        Process AI results and handle missing records.
        """
        
        if not all_results:
            self.logger.warning("No results returned from AI analysis")
            self.violations_data = pd.DataFrame(columns=[
                'Change_ID', 'Asset_Name', 
                'Requestor_ID', 'Requestor_Name', 
                'Developer_ID', 'Developer_Name', 
                'Deployer_ID', 'Deployer_Name', 
                'Approver_ID', 'Approver_Name', 
                'Status', 'Exception_Reason'
            ])
            return

        # Check for missing records
        processed_ids = set(result['change_id'] for result in all_results)
        original_ids = set(merged_df['Change_ID'])
        missing_ids = original_ids - processed_ids   

        if missing_ids:
            self.logger.warning(f"Some records were not processed: {missing_ids}")
            # Add missing records with a note
            for missing_id in missing_ids:
                missing_record = merged_df[merged_df['Change_ID'] == missing_id].iloc[0]
                all_results.append({
                    'change_id': missing_record['Change_ID'],
                    'asset_name': missing_record['Asset_Name'],
                    'requestor_id': missing_record['Requestor_ID'],
                    'requestor_name': missing_record['Requestor_Name'],
                    'developer_id': missing_record['Developer_ID'],
                    'developer_name': missing_record['Developer_Name'],
                    'deployer_id': missing_record['Deployer_ID'],
                    'deployer_name': missing_record['Deployer_Name'],
                    'approval_id': missing_record['Approver_ID'],
                    'approval_name': missing_record['Approver_Name'],
                    'status': 'Unknown',
                    'exception_reason': 'Record not processed by AI analysis'
                })
        # Create a DataFrame from the results
        results_df = pd.DataFrame(all_results) 

        # Merge with original data to get all relevant fields
        self.violations_data = pd.merge(
            results_df,
            merged_df,
            left_on=['change_id', 'asset_name'],
            right_on=['Change_ID', 'Asset_Name'],
            how='left'
        )

        # Rename columns for consistency
        self.violations_data = self.violations_data.rename(columns={
            'status': 'Status',
            'exception_reason': 'Exception_Reason'
        }) 

        # Drop duplicate columns
        if 'change_id' in self.violations_data.columns:
            self.violations_data = self.violations_data.drop(columns=['change_id', 'asset_name'])
    
        # Standardize exception reasons
        self._standardize_exception_reasons()   

        self.logger.info(f"Total records analyzed by AI: {len(self.violations_data)}")
        self.logger.info(f"Records with violations: {len(self.violations_data[self.violations_data['Status'] == 'Exception'])}")

    def _standardize_exception_reasons(self):
        """
        Standardize the exception reasons in the violations data.
        """
        if self.violations_data is None or 'Status' not in self.violations_data.columns:
            return            
        # Only process rows with Exception status
        exception_rows = self.violations_data['Status'] == 'Exception'  
        for idx in self.violations_data[exception_rows].index:
            row = self.violations_data.loc[idx] 
    
            # Group violations by user ID
            violations_by_id = {}
            # Check each user ID and collect the roles they perform
            user_roles = {
                row['Requestor_ID']: ['Requestor'],
                row['Developer_ID']: ['Developer'],
                row['Deployer_ID']: ['Deployer'],
                row['Approver_ID']: ['Approver']
            }

            # Consolidate roles by user ID
            for user_id, roles in list(user_roles.items()):
                # Skip unknown IDs
                if user_id == 'Unknown':
                    continue
                
                # Check if this ID appears in other roles
                if row['Requestor_ID'] == user_id and 'Requestor' not in roles:
                    roles.append('Requestor')
                if row['Developer_ID'] == user_id and 'Developer' not in roles:
                    roles.append('Developer')
                if row['Deployer_ID'] == user_id and 'Deployer' not in roles:
                    roles.append('Deployer')
                if row['Approver_ID'] == user_id and 'Approver' not in roles:
                    roles.append('Approver')
            
                # Only keep IDs with multiple roles (violations)
                if len(roles) > 1:
                    violations_by_id[user_id] = roles

            # Format the exception reasons
            reason_parts = []
            for user_id, roles in violations_by_id.items():
                if len(roles) == 4:  # All roles
                    reason_parts.append(f"Requestor, Developer, Deployer & Approver share the same ID ({user_id})")
                elif len(roles) == 3:  # Three roles
                    roles_str = ", ".join(roles[:-1]) + " & " + roles[-1]
                    reason_parts.append(f"{roles_str} share the same ID ({user_id})")
                elif len(roles) == 2:  # Two roles
                    reason_parts.append(f"{roles[0]} and {roles[1]} share the same ID ({user_id})")
            # Join all reason parts with semicolons
            if reason_parts:
                standardized_reason = "; ".join(reason_parts)            
                # Update the exception reason
                self.violations_data.at[idx, 'Exception_Reason'] = standardized_reason


    def load_verified_population_data(self):
        """
        Load change migration population data from verified population file.
        """
        try:
            self.logger.info("Loading verified population data")
            
            if not self.verified_population_file:
                # Find the verified population file with constant name
                verified_pop_dir = os.path.join(self.output_data_dir, "verified_populations")
                if not os.path.exists(verified_pop_dir):
                    self.logger.error(f"Verified populations directory not found at {verified_pop_dir}")
                    return False
                
                # Look for the constant filename instead of the latest file
                client_name = "Capgemini"  # You might want to make this configurable
                constant_filename = f"{client_name}_verified_population.xlsx"
                self.verified_population_file = os.path.join(verified_pop_dir, constant_filename)
                
                if not os.path.exists(self.verified_population_file):
                    self.logger.error(f"Verified population file not found at {self.verified_population_file}")
                    return False
                
                self.logger.info(f"Using verified population file: {self.verified_population_file}")
            
            # Load the Excel file
            self.logger.info(f"Loading data from {self.verified_population_file}")

            # Check if file exists
            if not os.path.exists(self.verified_population_file):
                self.logger.error(f"File does not exist: {self.verified_population_file}")
                return False
            
            # Load data from the Population Data sheet
            try:
                data = pd.read_excel(self.verified_population_file, sheet_name='Population Data')

                # Check if data is empty
                if data is None or data.empty:
                    self.logger.error("Population Data sheet is empty or could not be read")
                    return False
                
                # Check if required columns exist in change migration data
                required_columns = ['Change_ID', 'Asset_Name', 'Requestor_ID', 'Approver_ID', 'Developer_ID', ]
                missing_columns = [col for col in required_columns if col not in data.columns]

                if missing_columns:
                    self.logger.error(f"Missing required columns in change migration data: {missing_columns}")
                    return False
                
                self.change_migration_data = data
                self.logger.info(f"Loaded {len(self.change_migration_data)} records from verified population data")

                # Load metadata from the Metadata sheet
                try:
                    metadata_df = pd.read_excel(self.verified_population_file, sheet_name='Metadata')

                    # Convert metadata to dictionary
                    for _, row in metadata_df.iterrows():
                        key = row['Key']
                        value = row['Value']
                        self.metadata[key] = value
                
                    self.logger.info(f"Loaded metadata from verified population file")

                except Exception as e:
                    self.logger.warning(f"Error loading metadata sheet: {str(e)}")
                    # Continue even if metadata can't be loaded
                
                return True

            except Exception as e:
                self.logger.error(f"Error reading Excel file: {str(e)}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error loading verified population data: {str(e)}")
            return False    


    def load_cicd_deployment_logs(self):
        """
        Load deployment log data.
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
                return False
            
            self.deployment_log_data = data
            self.logger.info(f"Deployment log data loaded with {len(self.deployment_log_data)} records")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading deployment log data: {str(e)}")
            return False

    def load_doa_matrix_data(self):
        """
        Load DOA (Delegation of Authority) matrix data.
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
                return False
            
            self.doa_matrix_data = data
            self.logger.info(f"DOA matrix data loaded with {len(self.doa_matrix_data)} records")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading DOA matrix data: {str(e)}")
            return False

    def load_iam_users_data(self):
        """
        Load IAM users status data.
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
                return False
            
            self.iam_users_data = data
            self.logger.info(f"IAM users status data loaded with {len(self.iam_users_data)} records")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading IAM users status data: {str(e)}")
            return False
   


    def save_violations_report(self):
        """
        Save the SOD violations report with the specified format.
        """  
        try:
            self.logger.info("Saving SOD violations report - JSON NEW3") 

            # Check if we have results to save
            if not hasattr(self, 'violations_data') or self.violations_data is None:
                # If we have all_results but no violations_data, create it from all_results
                if 'all_results' in dir(self) and self.all_results:
                    self.logger.info(f"Creating violations_data from all_results ({len(self.all_results)} records)")
                    self.violations_data = pd.DataFrame(self.all_results)
                else:
                    self.logger.warning("No violations data to save, creating empty DataFrame")
                    self.violations_data = pd.DataFrame(columns=[
                        'Change_ID', 'Asset_Name', 
                        'Requestor_ID', 'Requestor_Name', 
                        'Developer_ID', 'Developer_Name', 
                        'Deployer_ID', 'Deployer_Name', 
                        'Approver_ID', 'Approver_Name', 
                        'Status', 'Exception_Reason'
                    ])
        
            # Create output directory if it doesn't exist
            output_dir = os.path.join(self.output_data_dir, "sod_violations")
            os.makedirs(output_dir, exist_ok=True)

            filename = f"sod_violations.xlsx"
            output_path = os.path.join(output_dir, filename)

            # Prepare metadata for the report
            report_metadata = {
                'report_timestamp': dt.now().strftime('%Y-%m-%d %H:%M:%S'),
                'generated_by': 'SODViolationDetectionAgent',
                'source_population_file': os.path.basename(self.verified_population_file) if self.verified_population_file else 'Unknown',
                'total_changes_analyzed': len(self.change_migration_data) if self.change_migration_data is not None else 0,
                'total_violations_found': len(self.violations_data[self.violations_data['Status'] == 'Exception']) if 'Status' in self.violations_data.columns and not self.violations_data.empty else 0,
                'environment': 'Development'
            }

            # Select and reorder columns for the output
            output_columns = [
                'Change_ID', 'Asset_Name', 
                'Requestor_ID', 'Requestor_Name', 
                'Developer_ID', 'Developer_Name', 
                'Deployer_ID', 'Deployer_Name', 
                'Approver_ID', 'Approver_Name', 
                'Status', 'Exception_Reason'
            ]

                # Create Excel writer
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Write violations data to sheet1
                if len(self.violations_data) > 0:
                    # Select only the columns that exist in the DataFrame
                    available_columns = [col for col in output_columns if col in self.violations_data.columns]
                    if available_columns:
                        output_df = self.violations_data[available_columns]
                        output_df.to_excel(writer, sheet_name='SOD Analysis', index=False)
                    else:
                        # Create an empty DataFrame with appropriate columns
                        pd.DataFrame(columns=output_columns).to_excel(writer, sheet_name='SOD Analysis', index=False)
                else:
                    # Create an empty DataFrame with appropriate columns
                    pd.DataFrame(columns=output_columns).to_excel(writer, sheet_name='SOD Analysis', index=False)
        
                # Write metadata to sheet2
                metadata_df = pd.DataFrame(list(report_metadata.items()), columns=['Key', 'Value'])
                metadata_df.to_excel(writer, sheet_name='Report Metadata', index=False)
    
            self.logger.info(f"SOD violations report saved to {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error saving SOD violations report: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False     
        

    def run(self):
        """
        Run the complete SOD violation detection workflow using AI.
        """
        try:
            self.logger.info("Starting SODViolationDetectionAgent")
    
            # Step 1: Load verified population data
            success = self.load_verified_population_data()
            if not success:
                self.logger.error("Failed to load verified population data")
                return False
            # Step 2: Load CI/CD deployment logs
            success = self.load_cicd_deployment_logs()
            if not success:
                self.logger.error("Failed to load CI/CD deployment logs")
                return False
            # Step 3: Load DOA matrix data
            success = self.load_doa_matrix_data()
            if not success:
                self.logger.error("Failed to load DOA matrix data")
                return False
            # Step 4: Load IAM users data
            success = self.load_iam_users_data()
            if not success:
                self.logger.error("Failed to load IAM users data")
                return False
            # Step 5: Detect SOD violations using AI
            success = self.detect_sod_violations_with_ai()
            if not success:
                self.logger.error("Failed to detect SOD violations with AI")
                return False
            # Step 6: Save violations report
            output_file = self.save_violations_report()
            if not output_file:
                self.logger.error("Failed to save violations report")
                return False
            self.logger.info(f"SODViolationDetectionAgent completed successfully. Output file: {output_file}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error running SODViolationDetectionAgent: {str(e)}")
            return False    
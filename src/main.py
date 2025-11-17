import asyncio
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from dotenv import load_dotenv
from azure.ai.agents.models import (
    Agent,
    AgentThread,
    AsyncFunctionTool,
    AsyncToolSet,
    CodeInterpreterTool,
    FileSearchTool,
    MessageRole,
    FilePurpose
)
import os, logging, sys

## All logs with level INFO and above (INFO, WARNING, ERROR, CRITICAL) will be displayed.
## DEBUG will be ignored.
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


load_dotenv()


# Validate required environment variables
required = ["PROJECT_ENDPOINT", "AGENT_MODEL_DEPLOYMENT_NAME"]
missing = [k for k in required if not os.environ.get(k)]
if missing:
    logger.error("Missing env vars: %s", ", ".join(missing))
    sys.exit(2)

# If validation passes, continue with your setup
PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT")
AGENT_MODEL_DEPLOYMENT_NAME = os.environ.get("AGENT_MODEL_DEPLOYMENT_NAME")



# Data Configuration
DATA_SHEET_FILE = "data/input/change_migration_listing.csv"
repo_root = Path(__file__).resolve().parents[1]
data_file_path = repo_root / "src" /DATA_SHEET_FILE
if not data_file_path.is_file():
    logger.error("Data file not found at %s", data_file_path)
    sys.exit(2)


async def main():
    # Agent client initialization
    client = AgentsClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        )
    )

    # Fetch the data to be analyzed
    directory = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(directory, DATA_SHEET_FILE)
    logger.info("Full data file path: %s", data_file)
    data_file_path = Path(data_file)

    with data_file_path.open('r') as file:
        data = file.read() + "\n"

    

    with client:
    
    # Upload data file
        try:
            file = client.files.upload_and_poll(
                file_path=data_file_path,
                purpose=FilePurpose.AGENTS
            )
            logger.info("Uploaded %s (id=%s)", file.filename, getattr(file, "id", None))
        except Exception as exc:
            logger.exception("Failed to upload data file: %s", exc)
            sys.exit(2)

        # Add tool
        toolset = AsyncToolSet()
        toolset.add(FileSearchTool())
        toolset.add(CodeInterpreterTool(file_ids=[file.id]))

        # Define an agent
        agent = client.create_agent(
            model=AGENT_MODEL_DEPLOYMENT_NAME,
            name="IdentifyChangeMigrationAgent",
            toolset=toolset,
            instructions="You are a helpful AI assistant"
        )
        logger.info("AgentName: %s", agent.name)


        #Create a thread for conversation
        thread = client.threads.create()    

        #Loop until user types 'exit'
        while True:
            user_input = await asyncio.to_thread(input, "User: ")
            if user_input.lower() == 'exit':
                break
            if len(user_input.strip()) == 0:
                print("Please enter a valid message.")
                continue

            # Send user input to the agent
            message = client.messages.create(
                thread_id=thread.id,
                content=user_input,
                role=MessageRole.USER
            )

            # Kick off the run 
            run = client.runs.create_and_process(
                thread_id=thread.id,
                agent_id=agent.id
            )

            #Check the run status for failures
            run_status = client.runs.get(thread_id=thread.id, run_id=run.id)
            if run_status.status in ("failed", "cancelled", "expired"):
                print(" The agent run failed or cancelled or expired. Please try again.", run.last_error)
                break

            #Show the latest response from the agent
            logger.info("Agent is typing...")

            
            # Fetch the latest assistant reply
            reply_text = client.messages.get_last_message_text_by_role(
                    thread_id=thread.id,
                    role=MessageRole.AGENT
            )


            # Get the agent's response
            if reply_text:
                print("Agent:", {reply_text.text.value})    


if __name__ == "__main__":
    print("Starting async program...")
    asyncio.run(main())
    print("Program finished.")
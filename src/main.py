
import asyncio
from azure.identity import DefaultAzureCredential
#from azure.ai.projects import AIProjectClient
from azure.ai.agents import AgentsClient

from azure.ai.agents.models import (
    Agent,
    AgentThread,
    AsyncFunctionTool,
    AsyncToolSet,
    CodeInterpreterTool,
    FileSearchTool,
    MessageRole,
)

from dotenv import load_dotenv
import os
load_dotenv()

## Get config from .env file
PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT")
AZURE_SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID")
AZURE_RESOURCE_GROUP_NAME = os.environ.get("AZURE_RESOURCE_GROUP_NAME")
AZURE_PROJECT_NAME = os.environ.get("AZURE_PROJECT_NAME")
AGENT_MODEL_DEPLOYMENT_NAME = os.environ.get("AGENT_MODEL_DEPLOYMENT_NAME")
API_KEY = os.environ.get("API_KEY")

print("PROJECT_ENDPOINT:", PROJECT_ENDPOINT)

async def main():
    # Agent client initialization (outside the context manager for global access)
    client = AgentsClient(
        endpoint = PROJECT_ENDPOINT,
        credential = DefaultAzureCredential
        (exclude_environment_credential=True,
         exclude_managed_identity_credential=True)
    )

    # Define an agent
    agent = client.create_agent(
        model = AGENT_MODEL_DEPLOYMENT_NAME,
        name = "Demo Agent",
        instructions = "You are a helpful AI assistant"
    )

    print("AgentName:", {agent.name})

    #Create a thread for conversation
    thread = client.threads.create()

    with client:
    #Loop until user types 'exit'
        while True:
            user_input = input("User: ")
            if user_input.lower() == 'exit':
                break
            if len(user_input.strip()) == 0:
                print("Please enter a valid message.")
                continue

            # Send user input to the agent
            message = client.messages.create(
                thread_id=thread.id,
                #agent_id=agent.id,
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
            print("Agent is typing...")

            
            # Fetch the latest assistant reply
            reply_text = client.messages.get_last_message_text_by_role(
                    thread_id=thread.id,
                    role=MessageRole.AGENT
            )


            # Get the agent's response
            if reply_text:
                print("Agent:", {reply_text.text.value})

    #clean up resources
    #client.delete_agent(agent.id)    


if __name__ == "__main__":
    print("Starting async program...")
    asyncio.run(main())
    print("Program finished.")
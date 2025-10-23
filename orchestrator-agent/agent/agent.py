import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, AsyncIterable, List

import httpx
import nest_asyncio
from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
    TaskState
)
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from .remote_agent_connection import RemoteAgentConnections

load_dotenv()
nest_asyncio.apply()

class HostAgent():

    def __init__(self):
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ""
        self._agent = self.create_agent()
        self._user_id = "host_agent"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            memory_service=InMemoryMemoryService(),
            session_service=InMemorySessionService(),
        )

    async def _async_init_components(self, remote_agent_addresses: List[str]):
            async with httpx.AsyncClient(timeout=30) as client:
                for address in remote_agent_addresses:
                    card_resolver = A2ACardResolver(client, address)
                    try:
                        card = await card_resolver.get_agent_card()
                        remote_connection = RemoteAgentConnections(
                            agent_card=card,
                            agent_url=address,
                        )
                        self.remote_agent_connections[card.name] = remote_connection
                        self.cards[card.name] = card
                    except httpx.ConnectError as e:
                        print(f"ERROR: Failed to get card from {address}: {e}")
                    except Exception as e:
                        print(f"ERROR: Failed to connect to agent at {address}: {e}")
            
            agent_info = [
                json.dumps({"name": card.name, "description": card.description})
                for card in self.cards.values()
            ]
            print(f"Agent info: {agent_info}")
            self.agents = "\n".join(agent_info) if agent_info else "No agents available."
    
    @classmethod
    async def create(cls, remote_agent_addresses: List[str]):
        instance = cls()
        await instance._async_init_components(remote_agent_addresses)
        return instance
    
    def create_agent(self) -> Agent:
        return Agent(
            name="Host_Agent",
            description="This Host agent that coordinates with remote agents to plan travel.",
            model="gemini-2.5-flash",
            instruction=self.root_instruction,
            tools=[
                self.send_message,
            ],
        )

    
    def root_instruction(self, context: ReadonlyContext) -> str:
        return f"""
        **Role:** You are the Host Agent, a travel planner. Your primary function is to coordinate with other agents to plan a trip

        **Core Directives:**

        *   **Task Delegation:** Use the `send_message` tool to delegate tasks to the appropriate agent
            *   Use the `airbnb_assistant` for any accommodation related queries
            *   Use the `Weather` for any weather related queries
        *   **Syntesize Information:** Take the information from the other agents and synthesize it to answer the user's query.
        *   **Transparent Communication:** Relay the final plan to the user.
        *   **Tool Reliance:** Strictly rely on available tools to address user requests. Do not generate responses based on assumptions.
        *   **Readability:** Make sure to respond in a concise and easy to read format (bullet points are good).

        **Today's Date (YYYY-MM-DD):** {datetime.now().strftime("%Y-%m-%d")}

        <Available Agents>
        {self.agents}
        </Available Agents>
        """
    
    async def stream(self, query: str, session_id: str ) -> AsyncIterable[dict[str, Any]]:
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )

        content = types.Content(role="user", parts=[types.Part.from_text(text=query)])
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                session_id=session_id,
                state={},
            )
        
        async for event in self._runner.run_async(user_id=self._user_id, session_id=session.id, new_message=content):
            if event.is_final_response():
                respose=""
                if(
                    event.content and event.content.parts and
                    event.content.parts[0].text
                ):
                    response = "\n".join(
                        [part.text for part in event.content.parts if part.text]
                    )
                yield {
                    "is_task_complete": True,
                    "content": response,
                }
            else:
                yield {
                    "is_task_complete": False,
                    "updates": "Host Agent is thinking..."
                }
    
    async def send_message(
        self, agent_name: str, task: str, tool_context: ToolContext
    ):
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f"Agent '{agent_name}' not found.")

        connection = self.remote_agent_connections[agent_name]

        if not connection:
            raise ValueError(f"Client not found for agent '{agent_name}'.")
        
        state = tool_context.state
        context_id = state.get("context_id", str(uuid.uuid4()))
        message_id = str(uuid.uuid4())

        payload = {
            "message": {
                "role" : "user",
                "parts": [
                    {
                        "type": "text",
                        "text": task,
                    }
                ],
                "messageId": message_id,
                "contextId": context_id,
            },
        }

        message_request = SendMessageRequest(
            id = message_id,
            params=MessageSendParams.model_validate(payload)
        )

        try:
            send_response: SendMessageResponse = await connection.send_message(message_request)
        except Exception as e:
            print(f"Error sending message to {agent_name}: {e}")
            return f"Error: Failed to send message to {agent_name}."

        print(f"Initial send message response from {agent_name}: {send_response}")

        if not isinstance(send_response.root, SendMessageSuccessResponse) or not isinstance(send_response.root.result, Task):
            print(f"Received a non-success or non-task response: {send_response}")
            return f"Error: Did not receive a valid task from {agent_name}. Response: {send_response}"
        
        current_task: Task = send_response.root.result
        
        print(f"Task {current_task.id} started. Polling for completion...")
        
        while current_task.status.state not in (
            TaskState.completed,
            TaskState.failed,
            TaskState.canceled,
        ):
            await asyncio.sleep(1)
            try:
                current_task = await connection.agent_client.get_task(
                    task_id=current_task.id
                )
                print(f"Task {current_task.id} status: {current_task.status.state.value}")
            except Exception as e:
                print(f"Error while polling task {current_task.id}: {e}")
                return f"Error: Failed to get task status from {agent_name}."

        if current_task.status.state != TaskState.completed:
            return f"Error: Task for {agent_name} failed with status {current_task.status.state.value}."

        print(f"Task {current_task.id} completed. Parsing artifacts...")
        
        resp = []
        if current_task.artifacts:
            for artifact in current_task.artifacts:
                if artifact.parts:
                    for part in artifact.parts:
                        if hasattr(part, 'root') and hasattr(part.root, 'text'):
                            resp.append(part.root.text)

        print(f"Returning final response from {agent_name}: {resp}")
        return resp
    
def _get_initialised_host_agent_sync():
        
    async def _async_main():

        friend_agent_urls = [
            "http://localhost:10002", # Hotel Agent
            "http://localhost:10003", # Weather Agent
        ]

        print("initializing host agent")

        hosting_agent_instance = await HostAgent.create(
                remote_agent_addresses=friend_agent_urls
            )
        print("HostAgent initialised")
        return hosting_agent_instance.create_agent()
        
    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            print(
            f"Warning: Could not initialize HostAgent with asyncio.run(): {e}. "
            "This can happen if an event loop is already running (e.g., in Jupyter). "
            "Consider initializing HostAgent within an async function in your application."
            )
        else:
            raise

root_agent = _get_initialised_host_agent_sync()
import logging
import os

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from agent import WeatherAgent
from agent_executor import WeatherAgentExecutor
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    host="localhost"
    port=10003

    try:
        capabilities = AgentCapabilities(streaming=False)

        skill = AgentSkill(
            id="weather_checker",
            name="Weather Checker",
            description="Check the weather for a particular date",
            tags=["weather", "season"],
            examples=[
                "Whats the weather tomorrow",
                "Whats the weather like next Tuesday",
            ],
        )

        agent_host_url = f"http://{host}:{port}"

        agent_card = AgentCard(
            name="Weather Agent",
            description="A friendly agent to check weather.",
            url=agent_host_url,
            version="1.0.0",
            default_input_modes=WeatherAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=WeatherAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill]
        )

        request_handler = DefaultRequestHandler(
            agent_executor=WeatherAgentExecutor(),
            task_store=InMemoryTaskStore()
        )

        server = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler
        )

        uvicorn.run(server.build(), host=host, port=port)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)


if __name__ == "__main__":
    main()
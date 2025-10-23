# A2A Multi Agent Travel Planner

## Description
This project is a multi-agent system for travel planning. It consists of three agents that communicate with each other using the Agent-to-Agent (a2a) communication protocol. The system can help you plan your trip by finding hotels and checking the weather.

## Getting Started

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/fatima-amani/a2a-multi-agent-travel-planner.git
    cd a2a-multi-agent-travel-planner
    ```

2.  **Install dependencies:**
    Make sure you have `uv` installed. Then run:
    ```bash
    uv sync
    ```

## Frameworks and Tools
*   **Orchestrator Agent:** This agent is the main coordinator. It is built using the `google.adk` framework.
*   **Hotel Agent:** This agent is responsible for finding and booking hotels. It is built using the `google.adk` framework and uses the `MCPToolset` to connect to the AirBNB MCP server, which exposes tools for interacting with AirBNB.
*   **Weather Agent:** This agent provides weather forecasts. It is built using the `crewai` framework and uses a custom tool to get weather data.

## Running the project
To run the project, you need to start each agent in a separate terminal.

**1. Start the AirBNB MCP Server:**
Before running the hotel agent, you need to start the AirBNB MCP server. To see the available options, run:
```bash
npx @openbnb/mcp-server-airbnb --help
```
To start the server, run:
```bash
npx @openbnb/mcp-server-airbnb
```

**2. Start the Hotel Agent:**
```bash
cd hotel-agent
uv run .
```
You can view the agent card at `http://localhost:10002/.well-known/agent-card.json`.

**3. Start the Weather Agent:**
```bash
cd weather-agent
uv run .
```
You can view the agent card at `http://localhost:10003/.well-known/agent-card.json`.

**4. Start the Orchestrator Agent:**
```bash
cd orchestrator-agent
uv run adk web
```
You can access the web UI for the orchestrator at `http://localhost:8000`.
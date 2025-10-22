import random
from datetime import date, datetime, timedelta

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters


async def get_tools_async():
    """
    Gets tools from the AirBNB MCP Server.
    """
    print("Attempting to connect to MCP AirBNB server...")
    tools, exit_stack = await MCPToolset.from_server(
        connection_params=StdioServerParameters(
        command='npx', 
        args=["-y",   
              "@openbnb/mcp-server-airbnb",
              "--ignore-robots-txt",
            ],
          )
        )
    print("MCP Toolset created successfully.")
    return tools, exit_stack


async def create_agent() -> LlmAgent:
    tools, exit_stack = await get_tools_async()
    print(f"Fetched tools from MCP: {tools}")
    return LlmAgent(
        model="gemini-2.5-flash",
        name='airbnb_assistant',
        instruction='Help user interact with the AirBNB website and listings.',
        tools=tools,
    )
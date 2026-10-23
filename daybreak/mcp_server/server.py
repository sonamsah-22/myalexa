"""
Streamable HTTP MCP Server for MyAlexa Daily Planner using official mcp FastMCP SDK.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    logger.error("The 'mcp' SDK is not installed. Please run: pip install mcp")
    sys.exit(1)

from daybreak.mcp_server.tools.planner_tools import (
    add_event,
    get_agenda,
    add_task,
    list_tasks,
    complete_task,
    plan_my_day
)

# Initialize FastMCP Server with host, port, streamable_http_path, and stateless_http=True
host_env = os.getenv("HOST", "0.0.0.0")
port_env = int(os.getenv("PORT", "8000"))

mcp = FastMCP(
    name="MyAlexa Daily Planner",
    instructions="Voice-first daily planner MCP server delivering concise, natural spoken responses for Alexa+.",
    host=host_env,
    port=port_env,
    streamable_http_path="/mcp",
    stateless_http=True
)

# Register tools with detailed guidance: WHEN to use + example spoken phrases
mcp.tool(
    name="add_event",
    description=(
        "Use when the user wants to schedule or add a new event, meeting, appointment, or calendar entry. "
        "Example phrases: 'Add a meeting with John tomorrow at 2 PM', 'Schedule team sync for 10 AM', "
        "'Put dentist appointment on my calendar'."
    )
)(add_event)

mcp.tool(
    name="get_agenda",
    description=(
        "Use when the user asks for their agenda, schedule, upcoming events, or daily overview. "
        "Example phrases: 'What's my day look like?', 'What do I have scheduled today?', "
        "'Show my agenda for tomorrow'."
    )
)(get_agenda)

mcp.tool(
    name="add_task",
    description=(
        "Use when the user wants to create a new task, to-do item, reminder, or action item. "
        "Example phrases: 'Add a task to call the dentist', 'Remind me to buy groceries', "
        "'Put finish report on my to-do list'."
    )
)(add_task)

mcp.tool(
    name="list_tasks",
    description=(
        "Use when the user asks for their pending tasks, to-do list, or items left to complete. "
        "Example phrases: 'What's on my to-do list?', 'Read my pending tasks', "
        "'What tasks do I need to finish?'."
    )
)(list_tasks)

mcp.tool(
    name="complete_task",
    description=(
        "Use when the user marks a task or to-do item as done, finished, or completed. "
        "Example phrases: 'Mark call dentist as done', 'I finished buying groceries', "
        "'Complete the report task'."
    )
)(complete_task)

mcp.tool(
    name="plan_my_day",
    description=(
        "Use when the user asks to plan their day, optimize their schedule, organize open tasks into free slots, "
        "or build a daily plan. Example phrases: 'Plan my afternoon', 'Organize my day', "
        "'Fit my open tasks into my schedule'."
    )
)(plan_my_day)


def main():
    logger.info(f"Starting MyAlexa MCP Server on http://{host_env}:{port_env}/mcp (STORAGE={os.getenv('STORAGE', 'memory')})")
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()

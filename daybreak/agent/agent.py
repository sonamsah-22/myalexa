"""
Strands Agent implementation for MyAlexa Daily Planner.
Integrates Strands Agent SDK, BedrockModel, and MCPClient over Streamable HTTP transport.
Includes fallback intent router when Bedrock model is not configured locally.
"""
import os
import sys
import asyncio
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("myalexa_agent")

SYSTEM_PROMPT = (
    "You are a voice assistant like Alexa. Reply in one or two short spoken sentences. "
    "Never use lists, markdown, or emojis. Use tools to act, then confirm briefly."
)

class MyAlexaAgent:
    """Voice agent connecting Strands Agent SDK with the Streamable HTTP MCP server."""
    
    def __init__(self, mcp_url: str = None):
        self.mcp_url = mcp_url or os.getenv("MCP_URL", "http://localhost:8000/mcp")
        self.bedrock_model_id = os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.strands_agent = None
        self.tools = []
        self._init_agent()

    def _init_agent(self):
        try:
            from strands.tools.mcp import MCPClient
            self.mcp_client = MCPClient(url=self.mcp_url)
            # Load tools from MCP server
            self.tools = asyncio.run(self.mcp_client.load_tools())
            logger.info(f"Loaded {len(self.tools)} tools from MCP server at {self.mcp_url}")
        except Exception as e:
            logger.warning(f"Failed to load MCP tools dynamically ({e}). Will use tool fallback.")

        # Attempt initializing Strands Agent with BedrockModel if AWS credentials exist
        try:
            from strands import Agent
            from strands.models import BedrockModel
            
            model = BedrockModel(
                model_id=self.bedrock_model_id,
                region_name=self.aws_region
            )
            self.strands_agent = Agent(
                model=model,
                tools=self.tools,
                system_prompt=SYSTEM_PROMPT
            )
            logger.info("Initialized Strands Agent with BedrockModel.")
        except Exception as e:
            logger.info(f"Strands BedrockModel not available ({e}). Using deterministic voice router fallback.")

    async def handle_request(self, user_prompt: str) -> Dict[str, Any]:
        """
        Process user prompt, execute required MCP tools, and return spoken response
        along with tool-call metadata for the UI inspector panel.
        """
        tool_calls_meta = []
        
        # 1. If Strands agent with Bedrock is available, run it
        if self.strands_agent:
            try:
                result = await self.strands_agent.invoke_async(user_prompt)
                return {
                    "response": str(result),
                    "tool_calls": getattr(result, "tool_calls", [])
                }
            except Exception as e:
                logger.warning(f"Strands agent run failed ({e}), using direct tool invocation router.")

        # 2. Direct Voice Intent Router Fallback (works locally without AWS/Bedrock setup)
        from daybreak.mcp_server.tools.planner_tools import (
            add_event,
            get_agenda,
            add_task,
            list_tasks,
            complete_task,
            plan_my_day
        )
        
        prompt_lower = user_prompt.strip().lower()
        spoken_response = ""

        if any(w in prompt_lower for w in ["plan", "organize", "schedule my day", "daily plan"]):
            name = "plan_my_day"
            args = {"date": "today"}
            result_str = plan_my_day(date="today")
            tool_calls_meta.append({"name": name, "args": args, "result": result_str})
            spoken_response = result_str

        elif any(w in prompt_lower for w in ["agenda", "schedule", "calendar", "what's on"]):
            name = "get_agenda"
            date_param = "tomorrow" if "tomorrow" in prompt_lower else "today"
            args = {"date": date_param}
            result_str = get_agenda(date=date_param)
            tool_calls_meta.append({"name": name, "args": args, "result": result_str})
            spoken_response = result_str

        elif any(w in prompt_lower for w in ["to-do", "tasks", "pending", "what do i need"]):
            name = "list_tasks"
            args = {}
            result_str = list_tasks()
            tool_calls_meta.append({"name": name, "args": args, "result": result_str})
            spoken_response = result_str

        elif "complete" in prompt_lower or "finish" in prompt_lower or "done" in prompt_lower or "marked" in prompt_lower:
            name = "complete_task"
            # Extract task name
            task_target = prompt_lower.replace("mark", "").replace("complete", "").replace("finish", "").replace("done", "").replace("as", "").strip()
            args = {"title_or_id": task_target or "task"}
            result_str = complete_task(title_or_id=task_target or "task")
            tool_calls_meta.append({"name": name, "args": args, "result": result_str})
            spoken_response = result_str

        elif "add event" in prompt_lower or "meeting" in prompt_lower or "appointment" in prompt_lower:
            name = "add_event"
            title = "Meeting"
            if "with" in prompt_lower:
                title = "Meeting " + prompt_lower.split("with")[-1].split("at")[0].strip()
            args = {"title": title.title(), "date": "today", "start_time": "14:00", "end_time": "15:00"}
            result_str = add_event(title=title.title(), date="today", start_time="14:00", end_time="15:00")
            tool_calls_meta.append({"name": name, "args": args, "result": result_str})
            spoken_response = result_str

        elif "add" in prompt_lower or "task" in prompt_lower or "remind" in prompt_lower or "buy" in prompt_lower or "call" in prompt_lower:
            name = "add_task"
            clean_title = user_prompt.lower()
            for prefix in ["add a task to", "add task", "add a task", "remind me to", "add"]:
                clean_title = clean_title.replace(prefix, "").strip()
            title = (clean_title or "New Task").capitalize()
            args = {"title": title, "due": "", "duration_min": 30}
            result_str = add_task(title=title, due="", duration_min=30)
            tool_calls_meta.append({"name": name, "args": args, "result": result_str})
            spoken_response = result_str

        else:
            spoken_response = f"I heard '{user_prompt}'. I can manage your agenda, add tasks, or plan your day. What would you like to do?"

        return {
            "response": spoken_response,
            "tool_calls": tool_calls_meta
        }


# Global agent instance
_agent_instance = None

def get_agent() -> MyAlexaAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = MyAlexaAgent()
    return _agent_instance

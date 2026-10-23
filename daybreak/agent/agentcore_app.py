"""
Bedrock AgentCore hosting application entrypoint for MyAlexa.
Registers BedrockAgentCoreApp entrypoint handler for cloud deployment on AWS Bedrock AgentCore Runtime.
"""
import logging
from bedrock_agentcore import BedrockAgentCoreApp
from daybreak.agent.agent import get_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentcore_app")

app = BedrockAgentCoreApp()

@app.entrypoint
async def entrypoint(payload: dict) -> dict:
    """
    AgentCore entrypoint accepting {"prompt": "..."} and returning {"response": "..."}.
    """
    prompt = payload.get("prompt", "")
    logger.info(f"AgentCore received prompt: {prompt}")
    
    agent = get_agent()
    result = await agent.handle_request(prompt)
    
    return {
        "response": result.get("response", ""),
        "tool_calls": result.get("tool_calls", [])
    }


if __name__ == "__main__":
    app.run()

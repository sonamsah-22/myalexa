"""
FastAPI local server for MyAlexa UI Simulator.
Serves the web UI and provides the /chat endpoint proxying to the Strands Agent.
"""
import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ui_app")

app = FastAPI(title="MyAlexa Alexa+ Voice Simulator")

# Enable CORS for local demoing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import agent lazily
from daybreak.agent.agent import get_agent


class ChatRequest(BaseModel):
    prompt: str


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    ui_path = Path(__file__).parent / "index.html"
    if ui_path.exists():
        return FileResponse(ui_path)
    return HTMLResponse("<h2>MyAlexa UI Simulator</h2><p>index.html not found.</p>")


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
    try:
        agent = get_agent()
        result = await agent.handle_request(request.prompt.strip())
        return result
    except Exception as e:
        logger.error(f"Error handling chat request: {e}")
        return {
            "response": "Sorry, I ran into a problem processing your request.",
            "tool_calls": []
        }


def main():
    import uvicorn
    host = os.getenv("UI_HOST", "0.0.0.0")
    port = int(os.getenv("UI_PORT", "3000"))
    logger.info(f"Starting MyAlexa Simulator UI at http://localhost:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

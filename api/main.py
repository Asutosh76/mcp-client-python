from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from client.mcp_client import MCPClient

load_dotenv()

class Settings(BaseSettings):
    server_script_path: str = "Path to your server script"

settings = Settings()

async def lifespan(app):
    client = MCPClient()
    try:
        connected = await client.connect_to_server(settings.server_script_path)
        if not connected:
            raise HTTPException(status_code=500, detail="Failed to connect to MCP server")
        
        app.state.mcp_client = client
    except Exception as e:
        client.logger.error(f"Error during MCPClient lifespan: {e}")
        raise
    finally:
        await client.cleanup()


app = FastAPI(title = "MCP Client API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],    
)


class QueryRequest(BaseModel):
    query: str
class Message(BaseModel):
    role: str
    content: Any

class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]
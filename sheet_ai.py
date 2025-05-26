# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import asyncio
from contextlib import asynccontextmanager
import os

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

# Initialize LLM (you'll need to set OPENAI_API_KEY environment variable)
llm = ChatOpenAI(model="gpt-4o")

server_params = StdioServerParameters(
    command="node",
    # Make sure to update to the full absolute path to your math_server.py file
    args=["/Users/aelbagoury/gdrive-mcp-server/dist/index.js"],
    env={
        "GOOGLE_APPLICATION_CREDENTIALS": os.environ.get("GOOGLE_APP_CREDS"),
        "MCP_GDRIVE_CREDENTIALS":  os.environ.get("MCP_SERVER_CREDS")
    },
)

# Create agent


async def create_agent():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Get tools
            tools = await load_mcp_tools(session)

            # Create and run the agent
            agent = create_react_agent(llm, tools)

            agent_response = await agent.ainvoke({"messages": "What is the name of my Drive file about diet"})

            return agent
            # agent_response = await agent.ainvoke({"messages": "What is the name of my Drive file about diet"})
            # return agent_response

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent2
    agent2 = await create_agent()
    yield


app = FastAPI(title="Chat Assistant API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str


# agent_executor

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     global agent
#     # agent = await create_agent()
#     yield

# app = FastAPI(lifespan=lifespan)


# Store sessions (in production, use a proper database)
# sessions: Dict[str, ConversationBufferMemory] = {}

# def get_or_create_session(session_id: str) -> ConversationBufferMemory:
#     if session_id not in sessions:
#         sessions[session_id] = ConversationBufferMemory(
#             memory_key="chat_history",
#             return_messages=True,
#             output_key="output"
#         )
#     return sessions[session_id]

@app.get("/")
async def root():
    return {"message": "Chat Assistant API is running"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()

                # Get tools
                tools = await load_mcp_tools(session)

                # Create and run the agent
                agent = create_react_agent(llm, tools)

                agent_response = await agent.ainvoke({"messages": request.message})
                response_messages = agent_response["messages"]
                return ChatResponse(
                    response=response_messages[-1].content,
                    session_id=request.session_id,
                    timestamp=datetime.now().isoformat()
                )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.delete("/chat/{session_id}")
async def clear_session(session_id: str):
    """Clear chat history for a specific session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": f"Session {session_id} cleared"}
    return {"message": f"Session {session_id} not found"}

@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    return {"sessions": list(sessions.keys())}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

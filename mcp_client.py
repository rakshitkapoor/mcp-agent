import gradio as gr
import os

from smolagents import CodeAgent, MCPClient
from smolagents.models import OpenAIServerModel

try:
    mcp_client = MCPClient(
        {"url": "http://127.0.0.1:7860/gradio_api/mcp/sse"}
    )
    tools = mcp_client.get_tools()

    openai_model = OpenAIServerModel(model_id='gpt-4o')
    agent = CodeAgent(tools=[*tools], model=openai_model, additional_authorized_imports=["json", "ast", "urllib", "base64"])

    demo = gr.ChatInterface(
        fn=lambda message, history: str(agent.run(message)),
        type="messages",
        examples=["Analyze the sentiment of the following text 'This is awesome'"],
        title="Agent with MCP Tools",
        description="This is a simple agent that uses MCP tools to answer questions.",
    )

    demo.launch()
finally:
    mcp_client.disconnect()

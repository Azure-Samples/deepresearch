from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import json
import asyncio
import os
from pathlib import Path
import time
import tracemalloc  # Import tracemalloc for memory allocation tracking

# Enable tracemalloc to trace memory allocations
tracemalloc.start()

# Import deep research functionality
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from azure.core.credentials import AzureKeyCredential
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END

from prompts import query_writer_instructions, summarizer_instructions, reflection_instructions, get_current_date
from formatting import deduplicate_and_format_sources, format_sources
from states import SummaryState, SummaryStateInput, SummaryStateOutput

from tavily import AsyncTavilyClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Azure Deep Research")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="app/templates")

# Store active connections
active_connections = {}
images = []

# Initialize Azure AI models
endpoint = os.getenv("AZURE_INFERENCE_ENDPOINT")
model_name = os.getenv("AZURE_DEEPSEEK_DEPLOYMENT")
key = os.getenv("AZURE_AI_API_KEY")

# Set up the AI model
deep_seek_model = AzureAIChatCompletionsModel(
    endpoint=endpoint,
    credential=AzureKeyCredential(key),
    model_name=model_name,  
)



# Helper function to strip thinking tokens
def strip_thinking_tokens(text: str):
    """
    Extract the content between <think> and </think> tags and remove them from the text.
    """
    thoughts = ""
    while "<think>" in text and "</think>" in text:
        start = text.find("<think>")
        end = text.find("</think>")
        # Extract the content between tags (excluding the tags themselves)
        thoughts += text[start + len("<think>"):end].strip() + "\n\n"
        # Remove the tags and their content from the original text
        text = text[:start] + text[end + len("</think>"):]
    return thoughts.strip(), text.strip()

# Step 1: Generate a query to search the web for the latest info
async def generate_query(state: SummaryState):
    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = query_writer_instructions.format(
        current_date=current_date,
        research_topic=state.research_topic
    )

    messages = [
        SystemMessage(content=formatted_prompt),
        HumanMessage(content="Generate a query for web search:"),
    ]

    # Use the model to analyze the summary and decide whether to continue research or finalize it
    result = await deep_seek_model.ainvoke(messages)
    
    thoughts, text = strip_thinking_tokens(result.content)

    # Send thinking update to client
    if state.websocket_id in active_connections:
        await active_connections[state.websocket_id].send({
            "type": "thinking", 
            "data": {"thoughts": thoughts}
        })

    query = json.loads(text)
    search_query = query['query']
    rationale = query['rationale']
    # Send update to client
    if state.websocket_id in active_connections:
        await active_connections[state.websocket_id].send({
            "type": "generate_query", 
            "data": {"query": search_query, "rationale": rationale, "thoughts": thoughts}
        })
    
    return {"search_query": search_query, "rationale": rationale}


# Step 2: Look for that info online and get the results in a specific format
async def web_research(state: SummaryState):
    tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    search_results = await tavily_client.search(
        state.search_query, 
        max_results=1, 
        max_tokens_per_source=1000,
        include_raw_content=False,
        include_images=True
    )
    
    for image in search_results.get('images', []):
        images.append(image)

    search_str = deduplicate_and_format_sources(search_results, max_tokens_per_source=1000)
    
    # Send update to client
    if state.websocket_id in active_connections:
        await active_connections[state.websocket_id].send({
            "type": "web_research", 
            "data": {
                "sources": search_results.get('results', []),
                "images": search_results.get('images', [])
            }
        })
    
    return {
        "sources_gathered": [format_sources(search_results)], 
        "research_loop_count": state.research_loop_count + 1, 
        "web_research_results": [search_str]
    }

# Step 3: Summarize web research results
async def summarize_sources(state: SummaryState):
    # Existing summary
    existing_summary = state.running_summary
    
    # Most recent web research
    most_recent_web_research = state.web_research_results[-1]
    
    # Build the human message
    if existing_summary:
        human_message_content = (
            f"<Existing Summary> \n {existing_summary} \n </Existing Summary>\n\n"
            f"<New Context> \n {most_recent_web_research} \n </New Context>"
            f"Update the Existing Summary with the New Context on this topic: \n <User Input> \n {state.research_topic} \n </User Input>\n\n"
        )
    else:
        human_message_content = (
            f"<Context> \n {most_recent_web_research} \n </Context>"
            f"Create a Summary using the Context on this topic: \n <User Input> \n {state.research_topic} \n </User Input>\n\n"
        )
    
    messages = [
        SystemMessage(content=summarizer_instructions),
        HumanMessage(content=human_message_content)
    ]

    # Use the model to analyze the summary and decide whether to continue research or finalize it
    result = await deep_seek_model.ainvoke(messages)
    
    thoughts, text = strip_thinking_tokens(result.content)

    # Send thinking update to client
    if state.websocket_id in active_connections:
        await active_connections[state.websocket_id].send({
            "type": "thinking", 
            "data": {"thoughts": thoughts}
        })

    running_summary = text
    
    # Send update to client
    if state.websocket_id in active_connections:
        await active_connections[state.websocket_id].send({
            "type": "summarize", 
            "data": {"summary": running_summary}
        })
    
    return {"running_summary": running_summary}

# Step 4: Reflect on the summary and identify areas for further research
async def reflect_on_summary(state: SummaryState):
    # Use the model to analyze the summary and decide whether to continue research or finalize it
    result = await deep_seek_model.ainvoke(
        [
            SystemMessage(content=reflection_instructions.format(research_topic=state.research_topic)),
            HumanMessage(content=f"Reflect on our existing knowledge: \n === \n {state.running_summary}, \n === \n And now identify a knowledge gap and generate a follow-up web search query:")
        ]
    )
    
    thoughts, text = strip_thinking_tokens(result.content)
    
    # Send thinking update to client
    if state.websocket_id in active_connections:
        await active_connections[state.websocket_id].send({
            "type": "thinking", 
            "data": {"thoughts": thoughts}
        })
    
    try:
        # Try to parse as JSON first
        reflection_content = json.loads(text)
        # Get the follow-up query
        query = reflection_content['follow_up_query']
        knowledge_gap = reflection_content['knowledge_gap']
        
        # Send reflection update to client
        if state.websocket_id in active_connections:
            await active_connections[state.websocket_id].send({
                "type": "reflection", 
                "data": {"query": query, "knowledge_gap": knowledge_gap}
            })
        
        # Check if query is None or empty
        if not query:
            # Use a fallback query
            return {"search_query": f"Tell me more about {state.research_topic}", "knowledge_gap": ""}
        return {"search_query": query, "knowledge_gap": knowledge_gap}
    except (json.JSONDecodeError, KeyError, AttributeError):
        # If parsing fails or the key is not found, use a fallback query
        fallback_query = f"Tell me more about {state.research_topic}"
        
        # Send fallback update to client
        if state.websocket_id in active_connections:
            await active_connections[state.websocket_id].send({
                "type": "reflection", 
                "data": {"query": fallback_query, "knowledge_gap": "Unable to identify specific knowledge gap"}
            })
            
        return {"search_query": fallback_query}

# Step 5: Finalize the summary
async def finalize_summary(state: SummaryState):
    # Format the final summary with images and sources
    
    # Add images section if any images were collected during research
    image_section = ""
    if images and len(images) >= 2:
        # Include the first two images at the top of the summary
        image_section = f"""
<div class="flex flex-col md:flex-row gap-4 mb-6">
  <div class="w-full md:w-1/2">
    <img src="{images[0]}" alt="Research image 1" class="w-full h-auto rounded-lg shadow-md">
  </div>
  <div class="w-full md:w-1/2">
    <img src="{images[1]}" alt="Research image 2" class="w-full h-auto rounded-lg shadow-md">
  </div>
</div>
"""
    elif images and len(images) == 1:
        # If only one image is available, display it centered
        image_section = f"""
<div class="flex justify-center mb-6">
  <div class="w-full max-w-lg">
    <img src="{images[0]}" alt="Research image" class="w-full h-auto rounded-lg shadow-md">
  </div>
</div>
"""
    
    # Add the image section at the beginning of the summary
    final_summary = f"{image_section}## Summary\n{state.running_summary}\n\n### Sources:\n"
    for source in state.sources_gathered:
        final_summary += f"{source}\n"
    
    # Send update to client
    if state.websocket_id in active_connections:
        await active_connections[state.websocket_id].send({
            "type": "finalize", 
            "data": {"summary": final_summary}
        })
    
    return {"running_summary": final_summary}

# Conditional function that decides whether to continue research or finalize summary
async def route_research(state: SummaryState):
    if state.research_loop_count <= 3:
        # Send update to client
        if state.websocket_id in active_connections:
            await active_connections[state.websocket_id].send({
                "type": "routing", 
                "data": {"decision": "continue", "loop_count": state.research_loop_count}
            })
        return "web_research"
    else:
        # Send update to client
        if state.websocket_id in active_connections:
            await active_connections[state.websocket_id].send({
                "type": "routing", 
                "data": {"decision": "finalize", "loop_count": state.research_loop_count}
            })
        return "finalize_summary"

# Set up the graph
def setup_graph():
    # Add nodes and edges
    builder = StateGraph(SummaryState, input=SummaryStateInput, output=SummaryStateOutput)
    builder.add_node("generate_query", generate_query)
    builder.add_node("web_research", web_research)
    builder.add_node("summarize_sources", summarize_sources)
    builder.add_node("reflect_on_summary", reflect_on_summary)
    builder.add_node("finalize_summary", finalize_summary)
    
    # Add edges
    builder.add_edge(START, "generate_query")
    builder.add_edge("generate_query", "web_research")
    builder.add_edge("web_research", "summarize_sources")
    builder.add_edge("summarize_sources", "reflect_on_summary")
    builder.add_conditional_edges("reflect_on_summary", route_research)
    builder.add_edge("finalize_summary", END)
    
    return builder.compile()

# WebSocket connection handler
class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
        
    def connect(self, websocket: WebSocket, client_id: str):
        # Store the websocket but don't call accept() here
        self.active_connections[client_id] = websocket
        active_connections[client_id] = self
        
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in active_connections:
            del active_connections[client_id]
            
    async def send(self, message: dict):
        if self.active_connections:  # Check if there are any connections
            client_id = list(self.active_connections.keys())[0]
            await self.active_connections[client_id].send_json(message)

# Initialize connection manager
manager = ConnectionManager()

# Routes
@app.get("/", response_class=HTMLResponse)
def get_html(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()  # Accept the connection first
    manager.connect(websocket, client_id)
    try:
        # Set up the graph
        graph = setup_graph()
        
        while True:
            data = await websocket.receive_text()
            data_json = json.loads(data)
            
            if data_json.get("type") == "research":
                # Clear images from previous research
                global images
                images = []
                
                # Start the deep research process
                research_topic = data_json.get("topic", "")
                
                # Stream graph execution
                async def stream_graph_updates():
                    is_research_complete = False
                    async for event in graph.astream({"research_topic": research_topic, "websocket_id": client_id}):
                        # Process events as needed
                        await asyncio.sleep(0.1)  # Small delay to avoid overwhelming the client
                        
                        # Extract the node name and state from the event
                        node_name = next(iter(event.keys()), None)
                        node_state = event.get(node_name, {})
                        
                        if node_name == "generate_query":
                            # Send query generation updates to the client
        
                            await manager.send({
                                "type": "generate_query", 
                                "data": {"query": node_state.get("search_query", ""),
                                         "rationale": node_state.get("rationale", "")}
                            })
                        elif node_name == "web_research":
                            # Send web research updates to the client
                            await manager.send({
                                "type": "web_research", 
                                "data": {
                                    "sources": node_state.get("sources_gathered"),
                                    "images": images  # Using the global images list
                                }
                            })
                        elif node_name == "summarize_sources":
                            # Send summary updates to the client
                            await manager.send({
                                "type": "summarize", 
                                "data": {"summary": node_state.get("running_summary", "")}
                            })
                        elif node_name == "reflect_on_summary":
                            # Send reflection updates to the client
                            await manager.send({
                                "type": "reflection", 
                                "data": {"query": node_state.get("search_query", ""),
                                         "knowledge_gap": node_state.get("knowledge_gap", "")}
                            })
                        elif node_name == "finalize_summary":
                            # Send final summary to the client
                            await manager.send({
                                "type": "finalize", 
                                "data": {"summary": node_state.get("running_summary", "")}
                            })
                            is_research_complete = True
                    
                    # Send a final message indicating research is complete
                    if is_research_complete:
                        await asyncio.sleep(0.5)  # Small delay to ensure all other messages are processed
                        await manager.send({
                            "type": "research_complete",
                            "data": {"status": "complete"}
                        })
                
                # Run graph execution in the background
                asyncio.create_task(stream_graph_updates())
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)

# Run with: uvicorn app.main:app --reload

"""
This is a sctrach file for running in interactive mode.
This means shift+enter in VSCode + Jupyter extension.
"""

# This is to include parent folder for imports
from path import Path
import sys
sys.path.append(Path.cwd().parent)
# This is to allow running this file in interactive mode
import asyncio
import nest_asyncio
nest_asyncio.apply()

# Imports
import os
from uuid import uuid4
from langgraph_sdk import get_sync_client
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, trim_messages
from langgraph.graph import MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages.utils import count_tokens_approximately
from langmem.short_term import summarize_messages

# Imported bots
from bot.brains.memory import memory_checkpointer, memory_store
from bot.main import graph
#from bot.bot_0 import graph
#from bot.cycle1.websearch_bot import graph, get_checkpointer as memory_checkpointer
#from bot.cycle2.first_bot import graph, get_graph_checkpointer as memory_checkpointer, get_graph_store as memory_store
#from bot.cycle2.main_memory_bot import graph
#from bot.cycle2.brains.memory import memory_store, memory_checkpointer

# Configuration for graph
user_id = "scratch_user"
thread_id = str(uuid4())
thread_id = "5667a262-fc09-4b93-9bf4-b677dbb0ebc8"
config = {"configurable": {"thread_id": thread_id}}
user_config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}


# Long-term memory store tests
async with memory_store() as store:
    memories = await store.asearch(("personal", user_id))

async with memory_checkpointer() as checkpointer:
    state = await checkpointer.aget(config=config)

messages = state["channel_values"].get("messages")

#### Streaming testing

## Quick checkpointing and store configuration
checkpointer = InMemorySaver()

## Async Store and state configuration
async_checpointer = memory_checkpointer()
checkpointer = await async_checpointer.__aenter__()
async_store = memory_store()
store = await async_store.__aenter__()

# CLOSE checkpointer and store at the end
await async_checpointer.__aexit__(None, None, None)
await async_store.__aexit__(None, None, None)

# Set the checkpointer and store to the graph
graph.checkpointer = checkpointer
graph.store = store
graph_generator_name = "massibot"

# Create a new thread
await graph.aupdate_state(user_config, None)
# Get current state
graph_state = await graph.aget_state(config)

# Message input
input_text = """Thanks! Actually, lets talk about food. I would like to have some good soup. Any ideas?"""
# "Prime" the graph with a message
up_resp = await graph.aupdate_state(user_config, MessagesState(messages=([HumanMessage(content=input_text)])), as_node="__start__")
checkpoint_id = up_resp["configurable"]["checkpoint_id"]
checkpoint_config = {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id, "user_id": user_id}}

# Invocation without sreaming
await graph.ainvoke({"messages": [HumanMessage(content=input_text)]}, config=user_config)




# Stream helper functions
def stream_thought(event):
    # Pick up tool results to stream thoughts to the UI
    if event["event"] == "on_chain_end":
        if event["name"] == "RunnableSequence" and event["data"]["output"].get("responses"):
            str_responses = str(event["data"]["output"]["responses"])
            return f"\nMemory accessed with: {str_responses}"
        if event["name"] == graph_generator_name and event["data"]["output"].get("messages") and hasattr(event["data"]["output"]["messages"][0], "tool_calls"):
            if tool_calls := event["data"]["output"]["messages"][0].tool_calls:
                if tool_calls[0].get("name") == "tavily_search_results_json":
                    return f"\nSearching web for: {tool_calls[0]['args']['query']}..."

def stream_token(event):
    # Pick up tokens from the main generator to stream to the UI
    if event["event"] == "on_chat_model_stream" and event["metadata"].get("langgraph_node") == graph_generator_name:
        if token := event["data"]["chunk"].content:
            return token


# Stream events from the graph
async for event in graph.astream_events(None, config=checkpoint_config):
    if token := stream_token(event):
        print(token, end="", flush=True)
    if thought := stream_thought(event):
        print(thought, end="", flush=True)



# Run the stream events to list for debugging
streamed_events = [event async for event in graph.astream_events(None, config=checkpoint_config)]
len(streamed_events)
for event in streamed_events:
    print(event["event"])
    
# Take only chain end events
chain_end_events = [event for event in streamed_events if event["event"] == "on_chain_end"]
len(chain_end_events)
for event in chain_end_events:
    if event["name"] == "RunnableSequence" and event["data"]["output"].get("responses"):
        print(str(event["data"]["output"]["responses"]))
    if event["name"] == graph_generator_name and event["data"]["output"].get("messages") and hasattr(event["data"]["output"]["messages"][0], "tool_calls"):
        if tool_calls := event["data"]["output"]["messages"][0].tool_calls:
            if tool_calls[0].get("name") == "tavily_search_results_json":
                print(f"Searching web for: {tool_calls[0]['args']['query']}...")
        

# Take only chat model stream events
chat_chunk_events = [event for event in streamed_events if event["event"] == "on_chat_model_stream" and event["metadata"].get("langgraph_node") == "massibot"]
len(chat_chunk_events)
for event in chat_chunk_events:
    print(event["data"]["chunk"].content, end="", flush=True)

for event in streamed_events:
    if token := stream_token(event):
        print(token, end="", flush=True)
    if thought := stream_thought(event):
        print(thought)



#### LangGraph client testing

BOT_URL = os.getenv("BOT_URL")
BOT_MASTER_KEY = os.getenv("MASTER_KEY")
client = get_sync_client(url=BOT_URL, headers={"X-Master-Key": BOT_MASTER_KEY})

bot_thread = client.threads.create(metadata={"graph_id": "bot", "user_id": user_id})
thread_id = bot_thread["thread_id"]

thread_state = client.threads.get_state(thread_id)
thread_state

human_message = HumanMessage(content="Joke about coffee.")
updated_state = client.threads.update_state(thread_id=thread_id,values={"messages": [human_message]}, as_node="__start__")
updated_state

configurable = updated_state["configurable"]
configurable

checkpoint_id = configurable["checkpoint_id"]
checkpoint_id

config = {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}

response = client.runs.wait(thread_id=thread_id, assistant_id="bot", config=config, checkpoint_id=checkpoint_id)
response


#### Messages manipulation tests

# Example messages for testing
messages = [
    HumanMessage(content="Hello! I am Miika and you are MassiBot."),
    AIMessage(content="Hello Miika! I am MassiBot, your friendly assistant."),
    HumanMessage(content="What is the weather in Helsinki at the moment?"),
    AIMessage(content="I can help you with that! The weather in Helsinki is sunny with a temperature of 20 degrees Celsius."),
    HumanMessage(content="I like pizza!"),
    AIMessage(content="I see you like pizza! Do you have a favorite topping?"),
    HumanMessage(content="Yes, I love pepperoni!"),
    AIMessage(content="Pepperoni is a classic choice! I can remember that you like pepperoni pizza.")
]

# Counting tokens
count_tokens_approximately(messages)

# Summary example
existing_summary = None
summary_llm = ChatOpenAI(model="gpt-4.1-nano").bind(max_tokens=128)
summ = summarize_messages(
        messages,
        running_summary=existing_summary,
        model=summary_llm,
        max_tokens=128,  
        max_summary_tokens=64
    )
summ.__dict__
summ.messages

# Trim messages example
trim_messages(
    state.values["messages"],
    strategy="last",
    token_counter=len,
    max_tokens=4,
    start_on="human",
    end_on=("human", "tool"),
    include_system=True,
)
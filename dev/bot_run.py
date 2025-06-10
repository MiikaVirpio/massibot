"""
BROKEN ATM DONT USE
This script is used to run the bot in a terminal.
Run from dev folder with: `python bot_run.py`
"""

# This is to include parent folder for imports
from path import Path
import sys
import asyncio
import aioconsole
sys.path.append(Path.cwd().parent)
from dotenv import load_dotenv
env_path = Path.cwd().parent / ".env"
load_dotenv(dotenv_path=env_path)

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# Interacts with the bot using the graph element itself
from bot.main import graph, get_graph_checkpointer, get_graph_store

# User id for memories and preferences
user_id = "vauhdikas"

# Set real thread_id
thread_id = "thread-233"
config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}

async def stream_graph_updates(user_input: str, graph):
    user_message = HumanMessage(content=user_input)
    thoughts = []
    tokens = ""
    #async for event in graph.astream({"messages": [user_message]}, config):
    async for event in graph.astream_events(input={"messages": [user_message]}, config=config, version="v1"):
        stream_out = False
        if thoughts == []:
            thoughts.append("Thinking...")
            stream_out = True
        if event["event"] == "on_chain_end" and event["name"] not in ["_write", "__start__", "__end__"] and event["data"]["output"] and isinstance(event["data"]["output"], dict):
            if output_messages := event["data"]["output"].get("messages"):
                for message in output_messages:
                    if hasattr(message, "tool_calls") and message.tool_calls:
                        if message.tool_calls[0]["name"] == "tavily_search_results_json":
                            thoughts.append(f"Searching web for: {message.tool_calls[0]['args']['query']}...")
                            stream_out = True
                        else:
                            thoughts.append(f"Calling tool: {message.tool_calls[0]['name']}.")
                            stream_out = True
                    if message.type == "tool":
                        if message.name == "tavily_search_results_json":
                            thoughts.append(f"Search success in {message.artifact.get('response_time')} seconds.")
                            stream_out = True
                        else:
                            thoughts.append(f"Tool {message.name} ready.")
                            stream_out = True
                    if message.type == "ai" and message.content and not tokens:
                        token = message.content
                        tokens += token
                        stream_out = True
        elif event["event"] == "on_chat_model_stream" and event["data"]["chunk"].content:
            token = event["data"]["chunk"].content
            tokens += token
            stream_out = True
        if stream_out:
            console_out = ""
            #if thoughts and not tokens:
            if thoughts:
                console_out += "".join([f'{thought}\n' for thought in thoughts])
            if tokens:
                console_out += tokens
            print(console_out, end="", flush=True)
            #for value in event.values():
            #    if messages := value.get("messages"):
            #        for message in messages[-1:]:
            #            if isinstance(message, AIMessage):
            #                if tool_calls := message.tool_calls:
            #                    for tool_call in tool_calls:
            #                        print(f"...calling tool: {tool_call['name']}.")
            #                
            #                else:
            #                    print(f"Bot: {message.content}")
            #            elif isinstance(message, ToolMessage):
            #                print("...got result from tool.")


## FIX THIS LATER AND DONT USE ##


async def main():
    async with get_graph_checkpointer() as checkpointer, get_graph_store() as store:
        graph.checkpointer = checkpointer
        graph.store = store
        while True:
            try:
                user_input = await aioconsole.ainput("Human: ")
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break
                await stream_graph_updates(user_input, graph)
            except Exception as e:
                print(f"An error occurred: {e}")
                break

if __name__ == "__main__":
    asyncio.run(main())

async with get_graph_checkpointer() as checkpointer, get_graph_store() as store:
        graph.checkpointer = checkpointer
        graph.store = store
        user_input = "Hello, do you remember me?"
        await stream_graph_updates(user_input, graph)
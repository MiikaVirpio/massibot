import os

from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults

"""
This was the beginning Base Artifact version for the bot before addition of retrieval tool.
"""

# State definition

class MassiBotState(MessagesState):
    summary: str

# Tools definition

search_tool = TavilySearchResults(max_results=5)
tools = [search_tool]

# Models definition

llm = ChatOpenAI(model="gpt-4o", max_tokens=200)
llm_tools = llm.bind_tools(tools)

# Nodes definition

def summarize(state: MassiBotState):
    if summary := state.get("summary"):
        summary_prompt = f"This is current summary: {summary}\n\nExtend the summary by conversation had above:"
    else:
        summary_prompt = "Summarize the conversation had above:"
    
    active_msg_count = 4
    past_messages = state["messages"][:-active_msg_count]  
    messages = past_messages + [HumanMessage(content=summary_prompt)]
    summary_response = llm.invoke(messages)
    del_history_messages = [RemoveMessage(id=message.id) for message in past_messages]
    return {"messages": del_history_messages, "summary": summary_response.content}

def bot(state: MassiBotState):
    messages = state.get("messages")
    if summary := state.get("summary"):
        summary_message = SystemMessage(content=f"Summary of conversation earlier: {summary}")
        messages = [summary_message] + messages
    response = llm_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools)

# Edges definition

def summary_cond(state: MassiBotState):
    summary_treshold = 14
    if len(state["messages"]) > summary_treshold:
        return "summarize"
    return "bot"

# Workflow

workflow = StateGraph(MassiBotState)
# Nodes (workers)
workflow.add_node("summarize", summarize)
workflow.add_node("bot", bot)
workflow.add_node("tools", tool_node)
# Edges (logic)

workflow.add_conditional_edges(START, summary_cond)
workflow.add_edge("summarize", "bot")
workflow.add_conditional_edges("bot", tools_condition)
workflow.add_edge("tools", "bot")

# Memory and Store

DB_URI = os.getenv("DB_URI")
# "langgraph dev" defaults to in-memory.
if DB_URI == ":memory:":
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_NAME = os.getenv("DB_NAME")
    DB_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?sslmode=disable"

def get_checkpointer():
    return AsyncPostgresSaver.from_conn_string(DB_URI)

# Graph

graph = workflow.compile()

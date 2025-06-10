import os

from pydantic import BaseModel, Field
from langgraph.func import entrypoint
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.config import get_store, get_config
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.tools.retriever import create_retriever_tool
from langgraph.store.postgres.aio import AsyncPostgresStore, PoolConfig
from langchain.embeddings import init_embeddings
from langmem import create_memory_store_manager
from langmem.short_term import summarize_messages, RunningSummary
from pydantic import BaseModel

"""
MassiBot.
"""

# Environment
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?sslmode=disable"
DB_URI2 = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?sslmode=disable"

# Models definition

llm = ChatOpenAI(model="gpt-4.1-nano")
summary_llm = llm.bind(max_tokens=128)

# Memory and Store

def get_graph_checkpointer():
    return AsyncPostgresSaver.from_conn_string(DB_URI)

def get_graph_store():
    return AsyncPostgresStore.from_conn_string(
        DB_URI,
        index={
        "dims": 1536,
        "embed": init_embeddings("openai:text-embedding-3-small"),
        "fields": ["text"]
        }
    )

class Trait(BaseModel):
    """Store interesting traits and characteristics of the user.
    Preferences, hobbies, something that can be used to personalize the conversation."""
    topic: str = Field(..., 
        description="Topic of the trait, e.g. 'vocation', 'preference', 'interest'")
    value: str = Field(...,
        description="Value of the trait, e.g. 'software engineer', 'likes pizza', 'enjoys hiking'")

user_memory_manager = create_memory_store_manager(
    llm,
    namespace=("memories", "{user_id}"),
    schemas=[Trait],
)

# State definition

class MassiBotState(MessagesState):
    summary: RunningSummary | None

# Tools definition



# Nodes definition

systen_prompt = """
You are a helpful assistant. Your name is MassiBot.
Your job is to ask questions and get to know the user.
You will use the memories of users traits to provide personalized responses and guide the conversation.
Start simple, and gradually build up the conversation.
Here are some memories for related to the user:

<memories>
{memories}
</memories>

"""
async def massibot(state: MassiBotState):
    state_messages = state.get("messages")
    print(f"LENGTH of state messages: {len(state_messages)}")
    summ = summarize_messages(
        state_messages,
        running_summary=state.get("summary"),
        model=summary_llm,
        max_tokens=256,  
        max_summary_tokens=128
    )
    print(f"LENGTH of summary messages: {len(summ.messages)}")
    trimmed_messages = summ.messages
    store= get_store()
    configurable = get_config()["configurable"]
    memories = await store.asearch(("memories", configurable["user_id"]))
    formatted_memories = "\n".join([f"{m.value['content']['topic']}: {m.value['content']['value']}" for m in memories])
    system_message = SystemMessage(content=systen_prompt.format(memories=formatted_memories))
    response = await llm.ainvoke([system_message] + trimmed_messages)
    await user_memory_manager.ainvoke({"messages": trimmed_messages[-1:]})
    if summ.running_summary:
        return {"messages": [response], "summary": summ.running_summary}
    else:
        return {"messages": [response]}

# Edges definition

# Workflow

workflow = StateGraph(MassiBotState)

# Nodes (workers)

workflow.add_node("massibot", massibot)

# Edges (logic)

workflow.set_entry_point("massibot")
workflow.add_edge("massibot", END)

# Graph


graph = workflow.compile()


async def make_graph():
    return workflow.compile(store=get_graph_store(), checkpointer=get_graph_checkpointer())
import asyncio
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from langgraph.graph import MessagesState
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.config import get_config
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, AnyMessage
from langchain_core.messages.utils import count_tokens_approximately
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.embeddings import init_embeddings
from langgraph.store.postgres.aio import AsyncPostgresStore
from langmem import create_memory_store_manager
from langmem.short_term import summarize_messages, RunningSummary, SummarizationResult
from mem0 import AsyncMemory

from bot.brains.config import settings, fast_llm, reasoning_llm, embeddings, summary_llm, mem0_conf

"""
State, store, and any memory management for MassiBot.
"""

# Short-Term Memory storage
def memory_checkpointer():
    return AsyncPostgresSaver.from_conn_string(settings.DB_URI.get_secret_value())

# Long-Term Memory (vector) storage
def memory_store():
    return AsyncPostgresStore.from_conn_string(settings.DB_URI.get_secret_value(), index={"dims": 1536,"embed": init_embeddings("openai:text-embedding-3-small"),"fields": ["text"]})

# Momentary memory state
class MassiBotState(MessagesState):
    summary: RunningSummary | None

# Input state
class InputState(BaseModel):
    input_messages: list[AnyMessage]
    input_summary: Optional[str] = None
    memories: list[str] = []

# Message state manager
async def make_summary(state: MassiBotState):
    """Manage summary in the state shortening message history context."""
    summary = summarize_messages(
        state.get("messages"),
        running_summary=state.get("summary"),
        model=summary_llm,
        max_tokens=1024, # Size of message history to compress (and when)
        max_summary_tokens=settings.SUMMARY_LENGTH, # Size of summary blob
    )
    return summary

# Long-Term Memory
memory = AsyncMemory(mem0_conf)

# Recall from long-term memory
async def recall_memory(state: MassiBotState):
    config = get_config()
    user_message = state.get("messages")[-1].content
    mem_results = await memory.search(query=user_message, user_id=config["configurable"]["user_id"], limit=10)
    return [mem["memory"] for mem in mem_results.get("results", [])]

# Memorize interaction to long-term memory
async def memorize_interaction(state: MassiBotState):
    def convert_message(message):
        if isinstance(message, HumanMessage):
            return {"role": "user", "content": message.content}
        elif isinstance(message, AIMessage):
            return {"role": "assistant", "content": message.content}
        else:
            print(f"WARNING: Unknown message type {type(message)}.")
    config = get_config()
    interaction = [convert_message(message) for message in state.get("messages")[-2:]]
    added_mem = await memory.add(interaction, user_id=config["configurable"]["user_id"])

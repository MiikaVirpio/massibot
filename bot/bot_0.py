from langgraph.graph import StateGraph, END, MessagesState
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

"""
Simplest format LLM API only workflow.
"""

llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0.7, max_tokens=256)

def language_model(state: MessagesState):
    messages = state.get("messages")
    response = llm.invoke(messages)
    return {"messages": [response]}

workflow = StateGraph(MessagesState)
workflow.add_node("llm", language_model)
workflow.set_entry_point("llm")
workflow.add_edge("llm", END)
graph = workflow.compile(checkpointer=InMemorySaver())

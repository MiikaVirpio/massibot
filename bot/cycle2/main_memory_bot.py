from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, END
from bot.cycle2.brains.memory import MassiBotState, recall, memorize

"""
This is the incredibly short code for main memory bot, since most of the logic is in the memory module.
This is the pinnacle of where Cycle 2 ended up.
"""

# Models
fast_llm = ChatOpenAI(model="gpt-4.1-nano")
reasoning_llm = ChatOpenAI(model="o4-mini")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Agent node
async def massibot(state: MassiBotState):
    # Recall from memory
    system_prompt, summary = await recall(state)
    # Call the LLM
    response = await fast_llm.ainvoke([system_prompt] + summary.messages)
    # Memorize and reflect
    await memorize(state, summary.messages + [response], summary)
    # Return the response
    agent_response = {"messages": [response]}
    if running_summary := summary.running_summary:
        agent_response["summary"] = running_summary
    return agent_response

workflow = StateGraph(MassiBotState)
workflow.add_node("massibot", massibot)
workflow.set_entry_point("massibot")
workflow.add_edge("massibot", END)

graph = workflow.compile()

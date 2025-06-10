from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage

from bot.brains.config import reasoning_llm
from bot.brains.prompts import MASSIBOT_PROMPT
from bot.brains.memory import MassiBotState, InputState, make_summary, recall_memory, memorize_interaction

"""
Small bonus just finishing the theses to have a functional memory bot.
Unifies the summary for long conversation and a long-term memory for little facts about the user.
Instructions are just to get to know to the user and to help them with their tasks.
"""

# Memory node
async def recall(state: MassiBotState):
    # Get summary from state summary and messages
    summary = await make_summary(state)
    if isinstance(summary.messages[0], SystemMessage):
        input_messages = summary.messages[1:]
    else:
        input_messages = summary.messages
    state_return = {"input_messages": input_messages}
    if summary.running_summary:
        state_return["summary"] = summary.running_summary
        state_return["input_summary"] = summary.running_summary.summary
    elif state_summary := state.get("summary"):
        state_return["input_summary"] = state_summary.summary
    # Recall memories from long-term memory
    memories = await recall_memory(state)
    if memories:
        state_return["memories"] = memories
    return state_return
    
# Agent node
async def massibot(state: InputState):
    today = datetime.now().strftime("%Y-%m-%d")
    system_instructions = MASSIBOT_PROMPT.format(
        today=today,
        prompt_memories=f"Memories from long-term memory:\n" + "\n".join(state.memories) + "\n\n" if state.memories else "",
        prompt_summary=f"Summary of previous conversation:\n{state.input_summary}\n\n" if state.input_summary else "",
    )
    system_message = SystemMessage(content=system_instructions)
    response = await reasoning_llm.ainvoke([system_message] + state.input_messages)
    return {"messages": [response]}

# Memorize node
async def memorize(state: MassiBotState):
    """Memorize the interaction to long-term memory."""
    await memorize_interaction(state)
    return

workflow = StateGraph(MassiBotState)
workflow.add_node("recall", recall)
workflow.add_node("massibot", massibot)
workflow.add_node("memorize", memorize)
workflow.set_entry_point("recall")
workflow.add_edge("recall", "massibot")
workflow.add_edge("massibot", "memorize")
workflow.add_edge("memorize", END)

graph = workflow.compile()
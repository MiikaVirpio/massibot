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

from bot.brains.config import settings, MEM0CONF
from bot.brains.prompts import MASSIBOT_PROMPT, PERSONAL_MEMORY_PROMPT, FINANCIAL_MEMORY_PROMPT


# Models
fast_llm = ChatOpenAI(model="gpt-4.1-nano")
reasoning_llm = ChatOpenAI(model="o4-mini")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
summary_llm = fast_llm.bind(max_tokens=256)


# Momentary memory state
class MassiBotState(MessagesState):
    summary: RunningSummary | None

# Message state manager
async def manage_state_messages(state: MassiBotState):
    """Manage summary in the state shortening message history context."""
    summary = summarize_messages(
        state.get("messages"),
        running_summary=state.get("summary"),
        model=summary_llm,
        max_tokens=512, # Size of message history to compress (and when)
        max_summary_tokens=256, # Size of summary blob
    )
    return summary

# Short-Term Memory storage
def memory_checkpointer():
    return AsyncPostgresSaver.from_conn_string(settings.DB_URI.get_secret_value())

# Long-Term Memory (vector) storage
def memory_store():
    return AsyncPostgresStore.from_conn_string(settings.DB_URI.get_secret_value(), index={"dims": 1536,"embed": init_embeddings("openai:text-embedding-3-small"),"fields": ["text"]})

# Personal memory
class UserPerson(BaseModel):
    """Store important personal details about the user related to identity and socioeconimic status."""
    name: Optional[str] = Field(None, description="The name of the user")
    name_in_use: Optional[str] = Field(None, description="The name the user prefers to be called")
    preferred_language: Optional[str] = Field(None, description="The preferred language of the user")
    taxation_country: Optional[str] = Field(None, description="The country where the user is taxed")
    city_of_residence: Optional[str] = Field(None, description="The city where the user resides")
    vocation: Optional[str] = Field(None, description="The user's vocation or profession")
    work_background: Optional[list[str]] = Field(None, description="The user's work background or history")
    age: Optional[str] = Field(None, description="The age of the user")
    family_and_household: Optional[list[str]] = Field(None, description="Information about the user's family and household")
    approximate_yearly_income: Optional[str] = Field(None, description="The user's approximate yearly income")
    subjective_investing_experience: Optional[str] = Field(None, description="The user's investing experience in their own words")
    subjective_risk_tolerance: Optional[str] = Field(None, description="The user's risk tolerance in their own words")
    skills_and_interests: Optional[list[str]] = Field(None, description="The user's skills and interests")
    other_personal_traits: Optional[list[str]] = Field(None, description="Other personal traits of the user that are relevant to financial advice")

# Personal memory manager
personal_memory_manager = create_memory_store_manager(
    fast_llm,
    schemas=[UserPerson],
    instructions=PERSONAL_MEMORY_PROMPT,
    enable_inserts=False,
    namespace=("personal", "{user_id}"),
)

# Personal memory recall fuction
async def recall_personal_memory(config) -> str:
    """Recall personal memory for the user."""
    personal_memory = await personal_memory_manager.asearch(config=config)
    print(f"Found {len(personal_memory)} personal memories.")
    # NOTE this is not working the model saves several memories (hence the -1 index)
    return f"""<User Personal>
    {str(personal_memory[-1].value.model_dump()) if len(personal_memory) > 0 else 'No personal memory found'}
    </User Personal>"""

# Personal memory memorize function
async def memorize_personal(messages, config):
    # Memorize every time with the pair of messages
    print(f"Memorizing personal memory with {len(messages)} messages.")
    await personal_memory_manager.ainvoke({"messages": messages}, config=config)

# Financial learning memory
class FinCurricula(BaseModel):
    """Store important learning, milestones, goals and growth of the user in money management to track progress."""
    topic: Optional[str] = Field(None, description="The topic of the financial learning")
    resources: Optional[list[str]] = Field(None, description="Resources used for financial learning")
    current_knowledge_level: Optional[str] = Field(None, description="The current knowledge level of the user in financial matters")
    goals: Optional[list[str]] = Field(None, description="Financial goals set by the user")
    achievements: Optional[list[str]] = Field(None, description="Achievements in financial learning")
class FinExperience(BaseModel):
    """Write the episode from the advisors perspective and include the user by highlighting the teamork and "we" expression. 
    Use the benefit of hindsight to record the memory, saving the teamworked process from experimentation to favourable conclusion so it can be learned from over time.
    Goal is to capture financial learning experiences that improve both agents advisory and users understanding and confidence in money management."""
    observation: Optional[str] = Field(None, description="The context and setup - what happened, what was the problem or goal")
    thoughts: Optional[str] = Field(None, description="Reasoning process as team and observations of reailizations of the user in the episode that led to the correct action and result. 'Then you ...'")
    action: Optional[str] = Field(None, description="What was done, how, and in what format. (Include whatever is salient to the success of the action). I ..",)
    result: Optional[str] = Field(None, description="Outcome and retrospective. What did you do well? What did the user do well? What could be improved for next time? We ...",)

financial_learning_manager = create_memory_store_manager(
    reasoning_llm,
    query_model=fast_llm,
    schemas=[FinCurricula, FinExperience],
    instructions=FINANCIAL_MEMORY_PROMPT,
    enable_inserts=True,
    namespace=("financial", "{user_id}"),
)

# Financial memory recall function
async def recall_financial_memory(config, query = None) -> str:
    """Recall financial learning memory for the user."""
    financial_memory = await financial_learning_manager.asearch(query=query, config=config, limit=10)
    print(f"Found {len(financial_memory)} financial learning memories.")
    return f"""<Financial Learning>
    {[str(mem.value.model_dump()) for mem in financial_memory] if financial_memory else 'No financial learning memory found'}
    </Financial Learning>"""

# Financial memory memorize function
async def memorize_financial(state, messages, config, summary: SummarizationResult | None = None):
    """Memorize financial learning along summary for performance"""
    # Triggering only on summary guarantees a fresh long context
    state_messages = state.get("messages")
    if not summary or not summary.running_summary or not state_messages:
        return
    
    # Looping from the end to the start to get the most recent messages
    cut_index = 0
    for message in state_messages[::-1]:
        if not isinstance(message, HumanMessage) and not isinstance(message, AIMessage):
            continue
        cut_index -= 1
        if message.id in summary.running_summary.summarized_message_ids:
            continue
        if count_tokens_approximately(state_messages[cut_index:]) > 1024: # Slide double the summary
            break
    # Add double window back and recent messages
    extended_conversation = state.get("messages")[cut_index:] + [messages[-1]]
    print(f"Memorizing financial learning with {len(extended_conversation)} messages.")
    await financial_learning_manager.ainvoke({"messages": extended_conversation}, config=config)

# Life-long learning memory
life_memory = AsyncMemory(MEM0CONF)

# Life-long learning recall
async def recall_life_memory(config, query: str = None) -> str:
    search_life = await life_memory.search(query=query, user_id=config["configurable"]["user_id"], limit=10)
    memorylist = search_life.get("results", [])
    print(f"Found {len(memorylist)} life-long learning memories.")
    memories = f"""<Memories>
    {[mem["memory"] for mem in memorylist] if len(memorylist) > 0 else 'No memories yet, make some!'}
    </Memories>"""
    return memories

# Memorize life-long learning
async def memorize_life(state, messages: list[AnyMessage], config):
    x = len(messages)
    # Weird problem of possible odd numbers
    if (x if x % 2 == 0 else x + 1) % 4 != 0:
        return
    # Every 4th message a context of max 20 extra messages
    state_messages = state.get("messages")
    # Sliding window to get context for discussion
    for i in range(2, 21, 2):
        if len(state_messages) < i:
            extra_context = state_messages
            break
        if count_tokens_approximately(state_messages[-i:] + messages) > 512:
            extra_context = state_messages[-i:]
            break
    def convert_message(message):
        if isinstance(message, HumanMessage):
            return {"role": "user", "content": message.content}
        elif isinstance(message, AIMessage):
            return {"role": "assistant", "content": message.content}
        else:
            print(f"WARNING: Unknown message type {type(message)}.")
    context_messages = [convert_message(message) for message in extra_context + messages if isinstance(message, (HumanMessage, AIMessage))]
    print(f"Memorizing life-long learning with {len(context_messages)} messages.")
    await life_memory.add(context_messages, user_id=config["configurable"]["user_id"])
    

async def recall(state: MassiBotState):
    """Recall any relevant memories for the user."""
    config = get_config()
    print(f"Recalling memories for user {config['configurable']['user_id']}.")
    input_string = state.get("messages")[-1].content if state.get("messages") else None
    # Recall and process
    personal_memory, financial_memory, memories, summary = await asyncio.gather(
        recall_personal_memory(config),
        recall_financial_memory(config, query=input_string),
        recall_life_memory(config, query=input_string),
        manage_state_messages(state),
    )
    if summary.running_summary:
        system_summary = summary.running_summary.summary
    else:
        system_summary = state.get("summary", "No summary available.")
    # Craft the most important, system prompt
    system_prompt = SystemMessage(content=MASSIBOT_PROMPT.format(
        agent=settings.AGENT_NAME,
        clock=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        personal=personal_memory,
        financial=financial_memory,
        memories=memories,
        summary=f"<Summary>\n{system_summary}\n</Summary>"
    ))
    print(f"System prompt: {count_tokens_approximately([system_prompt])} tokens. Active messages length: {len(summary.messages)}. State messages total: {len(state.get('messages'))}.")
    return system_prompt, summary

async def memorize(state: MassiBotState, messages: list[AnyMessage], summary: SummarizationResult | None = None):
    """Memorize the conversation and important details."""
    config = get_config()
    print(f"Memorizing for user {config['configurable']['user_id']}.")
    await asyncio.gather(
        memorize_personal(messages, config),
        memorize_financial(state, messages, config, summary),
        memorize_life(state, messages, config)
    )  # Fire and forget

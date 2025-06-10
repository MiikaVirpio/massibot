import os

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.tools.retriever import create_retriever_tool

"""
This is the main multi-agent workflow for Cycle 1.
"""

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_URI = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?sslmode=disable"

# State definition

class MassiBotState(MessagesState):
    question: str

# Postgres vector store as retriever
retriever = PGVector(
    embeddings=OpenAIEmbeddings(model="text-embedding-3-large"),
    collection_name="massi_docs",
    connection=DB_URI,
    use_jsonb=True,
    async_mode=True,
).as_retriever(search_type="mmr")

# Tools definition

retriever_tool = create_retriever_tool(
    retriever=retriever,
    name="retriever_tool",
    description="Tietokanta kaikkeen talousosaamiseen ja taloudellisiin elämäntilanteisiin liittyvään. Use for financial questions.",
    response_format="content_and_artifact",
)
search_tool = TavilySearchResults(max_results=5)

# Models definition

# o4-mini (1.1$/1M), chatgpt-4o-latest (5$/1M)
llm = ChatOpenAI(model="o4-mini")

# Nodes definition

def retriever_bot(state: MassiBotState):
    instruction = SystemMessage(
        content=f"""You are a helpful assistant that has a possibility to retrieve relevant documents from a database to answer the user's question.
        Any question with relevance to financial topics, especially in Finland or in finnish language, can be answered by retrieving documents from the database.
        Check carefully the original question is <question>{state.get('question')}</question> so form the retrieval query relevant to the question.
        """)
    messages = state.get("messages")
    response = llm.bind_tools([retriever_tool]).invoke([instruction] + messages)
    return {"messages": [response]}

def search_bot(state: MassiBotState):
    instruction = SystemMessage(
        content=f"""You are a helpful assistant that searches the web for revelevant information to answer the user's question.
        You will provide the last resort search results if the retriever does not return relevant documents.
        Check carefully the original question is <question>{state.get('question')}</question> so form the search query accordingly, 
        and dont mind the retrieved documents.
        """)
    messages = state.get("messages")
    response = llm.bind_tools([search_tool]).invoke([instruction] + messages)
    return {"messages": [response]}

# Edges definition

def grader_bot(state: MassiBotState):
    class Grade(BaseModel):
        score: str = Field(description="Binary score 'yes' or 'no' indicating relevance of the document to the question.")
    grader_instructions = (
        "You are a grader assessing relevance of a retrieved document to a user question. \n "
        "Here is the retrieved document: \n\n {found_doc} \n\n"
        f"Here is the user question: {state.get('question')} \n"
        "If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n"
        "Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."
    )
    for found_doc in state.get("messages")[-1].artifact:
        grade = llm.with_structured_output(Grade).invoke(
            grader_instructions.format(found_doc=found_doc.page_content))
        if grade.score == "no":
            state.get("messages")[-1].artifact.remove(found_doc)
    # Replace the content with remaining documents if any
    if state.get("messages")[-1].artifact:
        state.get("messages")[-1].content = "\n\n".join(
            [doc.page_content for doc in state.get("messages")[-1].artifact])
        # More than 2 good documents, we can move back for generation
        if len(state.get("messages")[-1].artifact) > 2:
            return "retriever_bot"
    else:
        state.get("messages")[-1].content = "No relevant documents found."
    return "search_bot"

# Workflow

workflow = StateGraph(MassiBotState)

# Nodes (workers)

workflow.add_node("store_question", lambda state: {"question": state["messages"][-1].content})
workflow.add_node("retriever_bot", retriever_bot)
workflow.add_node("retriever_tool", ToolNode([retriever_tool]))
workflow.add_node("search_bot", search_bot)
workflow.add_node("search_tool", ToolNode([search_tool]))

# Edges (logic)

workflow.add_edge(START, "store_question")
workflow.add_edge("store_question", "retriever_bot")
workflow.add_conditional_edges("retriever_bot", tools_condition, {"tools": "retriever_tool", END: END})
workflow.add_conditional_edges("retriever_tool", grader_bot)
workflow.add_conditional_edges("search_bot", tools_condition, {"tools": "search_tool", END: END})
workflow.add_edge("search_tool", "retriever_bot")

# Memory and Store

def get_checkpointer():
    return AsyncPostgresSaver.from_conn_string(DB_URI)

# Graph

graph = workflow.compile()

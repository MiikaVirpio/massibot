import os
import csv
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_postgres import PGVector
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, RemoveMessage
from langchain.tools.retriever import create_retriever_tool

"""
This is the semi-synthetic dataset creator bot coded in a whim at the end of Cycle 1 to create dataset that can be fine-tune with.
It is a simple bot that retrieves documents from the vector database and generates a question and an answer based on the retrieved documents.
"""


DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_URI = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?sslmode=disable"

class WorkingState(MessagesState):
    question: str
    answer: str

retriever = PGVector(
    embeddings=OpenAIEmbeddings(model="text-embedding-3-large"),
    collection_name="massi_docs",
    connection=DB_URI,
    use_jsonb=True,
    async_mode=True,
).as_retriever(search_type="mmr")
retriever_tool = create_retriever_tool(
    retriever=retriever,
    name="retriever_tool",
    description="""Vector database for financial knowledge and life situations.
    Use for financial questions. Data is in Finnish language, so query in Finnish."""
)

llm = ChatOpenAI(model="o4-mini").bind_tools([retriever_tool])

def creative_bot(state: WorkingState):
    accepted_questions = []
    with open("bot/dataset.csv", "r", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row:
                accepted_questions.append(row[0])
    
    
    
    class QuestionAnswer(BaseModel):
        question: str = Field(description="The question that a person with lower financial literacy might ask.")
        answer: str = Field(description="A helpful response to the question, strictly following the retrieved documents.")
    instruction = f"""You are a creative assistant helping to create a Q&A dataset.
    Your task is to generate a query for vector database of a topic a person with lower financial literacy might ask.
    You have a vector database that contains text for saving, investing, taxes, money management, budgeting, and other financial topics.
    Once received the the documents, you will generate a question and an answer based on the retrieved documents.
    The question should be in Finnish language, and the answer should be a helpful response to the question, strictly following the retrieved documents.
    Below is the list of previously accepted questions, make sure to generate something new and different:
    {chr(10).join(str(que) for que in accepted_questions)}
    """
    messages = state.get("messages")
    if messages[-1].type == "tool":
        questionanswer = llm.with_structured_output(QuestionAnswer).invoke([instruction] + messages)
        message = f"Question: {questionanswer.question}\nAnswer: {questionanswer.answer}"
        return {"question": questionanswer.question, "answer": questionanswer.answer, "messages": [message]}
    else:
        query = llm.invoke([instruction] + messages)
        return {"messages": [query]}

def human_oversight(state: WorkingState):
    #approved = True  # Only good stuff all the time
    approved = interrupt({
        "1_question": state.get("question"),
        "2_answer": state.get("answer"),
    })
    if approved:
        return Command(goto="saver")
    else:
        message = HumanMessage(content=f"""Please generate a new question and answer based on the retrieved documents.
        Previous question and anaswere were not suitable for the dataset. Refine the question to be dirrefent than before
        and tightly alinged with the retrieved documents. Previous question answer pair was:
        Question: {state.get("question")}
        Answer: {state.get("answer")}
        Please generate a new question and answer.""")
        messages = [RemoveMessage(id=msg.id) for msg in state.get("messages")] + [message]
        return Command(goto="creative_bot", update={"question": None, "answer": None, "messages": messages})

def csv_saver(state: WorkingState):
    with open("bot/dataset.csv", "a", newline="", encoding="utf-8") as csvfile:
        message = HumanMessage(content=f"""Please generate a new question and answer based on the retrieved documents.
        Previous question and anaswere were excellent for the dataset!. Make sure to create something new and different compared to previous.
        Especially the answer should reflect the expert knowledge from the retrieved documents.
        Previous question answer pair was:
        Question: {state.get("question")}
        Answer: {state.get("answer")}
        Please generate a new question and answer.""")
        writer = csv.writer(csvfile)
        # conver linebreaks to \n for csv compatibility
        state["question"] = state.get("question").replace("\n", "\\n")
        state["answer"] = state.get("answer").replace("\n", "\\n")
        writer.writerow([state.get("question"), state.get("answer")])
        
        messages = [RemoveMessage(id=msg.id) for msg in state.get("messages")] + [message]
    return {"question": None, "answer": None, "messages": messages}

workflow = StateGraph(WorkingState)
workflow.add_node("creative_bot", creative_bot)
workflow.add_node("retriever_tool", ToolNode([retriever_tool]))
workflow.add_node("human_oversight", human_oversight)
workflow.add_node("saver", csv_saver)
workflow.set_entry_point("creative_bot")
workflow.add_conditional_edges("creative_bot", tools_condition, {"tools": "retriever_tool", END: "human_oversight"})
workflow.add_edge("retriever_tool", "creative_bot")
workflow.add_edge("saver", "creative_bot")


checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

from contextlib import asynccontextmanager
import logging
import orjson
from uuid import uuid4
from datetime import datetime, timezone
from typing import List, Optional, Any

from fastapi import FastAPI, APIRouter, Security, HTTPException
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings
from langgraph.graph import MessagesState

from bot.brains.memory import memory_checkpointer, memory_store
from bot.main import graph
graph_streamers = ["massibot"]

logger = logging.getLogger("uvicorn.error")

class Settings(BaseSettings):
    MASTER_KEY: SecretStr

settings = Settings()

def check_master_key(api_key: str = Security(APIKeyHeader(name="X-Master-Key"))):
    if api_key != settings.MASTER_KEY.get_secret_value():
        raise HTTPException(401, "Invalid Master Key")


#def set_checkpointer(func):
#    @wraps(func)
#    async def wrapper(*args, **kwargs):
#        async with get_graph_checkpointer() as checkpointer, get_graph_store() as store:
#            graph.checkpointer = checkpointer
#            graph.store = store
#            return await func(*args, **kwargs)
#    return wrapper

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the graph with the checkpointer and store
    # Remark: This deployed as server would not be production grade. As function, ok (I guess?).
    async with memory_checkpointer() as checkpointer, memory_store() as store:
        graph.checkpointer = checkpointer
        graph.store = store
        print(f"INIT {graph.checkpointer}")
        print(f"INIT {graph.store}")
        yield  # This will keep the app running until shutdown
        print(f"SHUTDOWN {graph.checkpointer}")
        print(f"SHUTDOWN {graph.store}")


app = FastAPI(root_path="/bot", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:8000"], # Live Server extension and Django
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Main Router - LangGraph Server imitating API
main_router = APIRouter(dependencies=[Security(check_master_key)])

@main_router.get("/status")
async def get_status():
    try:
        str_store = str(graph.store.conn)
        str_checkpointer = str(graph.checkpointer.conn)
    except Exception as e:
        logger.error(f"GET STATUS ERROR: {e}")
        return {"error": str(e)}
    return {
        "store": str_store,
        "checkpointer": str_checkpointer,
    }

@main_router.get("/threads/{thread_id}/state")
#@set_checkpointer
async def get_thread_state(thread_id: str):
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = await graph.aget_state(config)
    except Exception as e:
        logger.error(f"GET THREAD STATE ERROR: {e}")
        return {"error": str(e)}
    return {
        "values": state.values,
        "metadata": state.metadata,
        "created_at": state.created_at,
    }


class PostThreads(BaseModel):
    thread_id: dict | None = str(uuid4())
    metadata: dict | None = {}

@main_router.post("/threads")
#@set_checkpointer
async def create_thread(payload: PostThreads):
    try:
        config = {"configurable": {"thread_id": payload.thread_id}}
        await graph.aupdate_state(config, None)
    except Exception as e:
        logger.error(f"CREATE THREAD ERROR: {e}")
        return {"error": str(e)}
    return {
        "thread_id": payload.thread_id,
        "metadata": payload.metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


class UpdateStateInput(BaseModel):
    values: dict

@main_router.post("/threads/{thread_id}/state")
#@set_checkpointer
async def update_thread_state(thread_id: str, payload: UpdateStateInput):
    try:
        config = {"configurable": payload.values["configurable"]}
        assert thread_id == config["configurable"]["thread_id"], "Thread ID mismatch"
        state_values = MessagesState(messages=payload.values["messages"])
        updated_state = await graph.aupdate_state(config, state_values, as_node="__start__")
        checkpoint_id = updated_state["configurable"]["checkpoint_id"]
    except Exception as e:
        logger.error(f"UPDATE THREAD STATE ERROR: {e}")
        return {"error": str(e)}
    return {
        "checkpoint_id": checkpoint_id,
    }


class RunWaitInput(BaseModel):
    input: dict
    assistant_id: str
    user_id: Optional[str] = None

@main_router.post("/threads/{thread_id}/runs/wait")
@main_router.post("/runs/wait")
#@set_checkpointer
async def run_wait(payload: RunWaitInput, thread_id: str = str(uuid4())):
    try:
        config = {"configurable": {"thread_id": thread_id}}
        if payload.user_id:
            config["configurable"]["user_id"] = payload.user_id
        result = await graph.ainvoke(payload.input, config)
    except Exception as e:
        logger.error(f"RUN WAIT ERROR: {e}")
        return {"error": str(e)}
    return result

class SearchStoreInput(BaseModel):
    namespace_prefix: List[str]
    filter: Optional[dict[str, Any]] = None
    limit: int = 10
    offset: int = 0

@main_router.post("/store/items/search")
#@set_checkpointer
async def search_store(payload: SearchStoreInput):
    try:
        store_result = await graph.store.asearch(
            tuple(payload.namespace_prefix),
            filter=payload.filter,
            limit=payload.limit,
            offset=payload.offset
        )
        itemlist = []
        for item in store_result:
            itemlist.append({
                "namespace": list(item.namespace),
                "key": item.key,
                "value": item.value,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            })
            
    except Exception as e:
        logger.error(f"SEARCH STORE ERROR: {e}")
        return {"error": str(e)}
    return {"items": itemlist}


# HTML Router - Serving Htmx in Django templates
html_router = APIRouter()

@html_router.get("/sse-html/{thread_id}/{checkpoint_id}")
async def sse_html(thread_id: str, checkpoint_id: str):
    async def stream_generator():
        try:
            # First analyze the state of the thread
            state = await graph.aget_state(config={"configurable": {"thread_id": thread_id}})
            if state.next == ():
                # Error, this state is not supposed to be initiated.
                logger.error(f"Thread {thread_id} has no next state, cannot stream.")
                yield "event: close\ndata: \n\n"
                return
            if state.values["messages"] and state.values["messages"][-1].type != "human":
                # Error state, last message is not a HumanMessage.
                logger.error(f"Thread {thread_id} last message is not a HumanMessage, cannot stream.")
                yield "event: close\ndata: \n\n"
                return
            if not state.metadata.get("user_id"):
                # Error state, no user_id in metadata.
                logger.error(f"Thread {thread_id} has no user_id in metadata, cannot stream.")
                yield "event: close\ndata: \n\n"
                return
            # Initialize variables for streaming
            config = {"configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "user_id": state.metadata.get("user_id")},
            }
            thoughts = []
            tokens = ""
            tool_streamed = {"UserPerson": False}
            # Start streaming!
            async for event in graph.astream_events(None, config=config, version="v1"):
                stream_out = False
                if thoughts == []:
                    thoughts.append("Thinking...")
                    stream_out = True
                if event["event"] == "on_chain_end" and event["name"] not in ["_write", "__start__", "__end__"] and event["data"]["output"] and isinstance(event["data"]["output"], dict):
                    if output_messages := event["data"]["output"].get("messages"):
                        for message in output_messages:
                            if hasattr(message, "tool_calls") and message.tool_calls:
                                for tool_call in message.tool_calls:
                                    if tool_name := tool_call.get("name"):
                                        if tool_name == "UserPerson":
                                            if not tool_streamed["UserPerson"]:
                                                thoughts.append("Memory accessed.")
                                                tool_streamed["UserPerson"] = True
                                                stream_out = True
                                        elif tool_name == "tavily_search_results_json":
                                            thoughts.append(f"Searching web for: {tool_call['args']['query']}...")
                                            stream_out = True
                                        else:
                                            logger.error(f"Unknown tool: tool_name:[{tool_name}], tool_name_type:[{type(tool_name)}]")
                            elif hasattr(message, "type") and message.type:
                                if message.type == "human":
                                    pass # No need to stream human message
                                elif message.type == "system":
                                    pass # No need to stream system message
                                elif message.type == "tool":
                                    if message.name == "UserPerson":
                                        pass # No need to stream UserPerson return
                                    elif message.name == "tavily_search_results_json":
                                        thoughts.append(f"Search success in {message.artifact.get('response_time')} seconds.")
                                        stream_out = True
                                    else:
                                        thoughts.append(f"Tool {message.name} ready.")
                                        stream_out = True
                                elif message.type == "ai":
                                    if message.content:
                                        if not tokens:
                                            token = message.content.replace("\n", "<br>")
                                            tokens += token
                                            stream_out = True
                                    else:
                                        logger.error(f"Unknown AI message of type {type(message)} without content: {message}")
                                else:
                                    logger.error(f"Unknown type {type(message.type)} of type: {message.type}")
                elif event["event"] == "on_chat_model_stream" and event["data"]["chunk"].content:
                    if not event.get("metadata").get("ls_max_tokens") or event.get("metadata").get("ls_max_tokens") != 256:
                        token = event["data"]["chunk"].content.replace("\n", "<br>")
                        tokens += token
                        stream_out = True
                if stream_out:
                    html_out = ""
                    if thoughts and not tokens:
                    #if thoughts:
                        html_out += "".join([f'{thought}<br>' for thought in thoughts])
                    if tokens:
                        html_out += tokens
                    yield f"event: chunk\ndata: {orjson.dumps(html_out).decode()[1:-1]}\n\n"
        except Exception as e:
            logger.error(f"STREAM GENERATOR ERROR: {e}")
        yield "event: close\ndata: \n\n"
        return
    return StreamingResponse(stream_generator(), media_type="text/event-stream")

@html_router.get("/sse-html2/{thread_id}/{checkpoint_id}")
async def sse_html2(thread_id: str, checkpoint_id: str):
    
    # Pick up tool results to stream thoughts to the UI
    def stream_thought(event):
        if event["event"] == "on_chain_end":
            if event["name"] == "RunnableSequence" and event["data"]["output"].get("responses"):
                str_responses = str(event["data"]["output"]["responses"])
                return f"\nMemory accessed with: {str_responses}"
            if event["name"] in graph_streamers and event["data"]["output"].get("messages") and hasattr(event["data"]["output"]["messages"][0], "tool_calls"):
                if tool_calls := event["data"]["output"]["messages"][0].tool_calls:
                    if tool_calls[0].get("name") == "tavily_search_results_json":
                        return f"\nSearching web for: {tool_calls[0]['args']['query']}..."
    
    # Pick up tokens from the main generator to stream to the UI
    def stream_token(event):
        if event["event"] == "on_chat_model_stream" and event["metadata"].get("langgraph_node") in graph_streamers:
            if token := event["data"]["chunk"].content:
                return token.replace("\n", "<br>")
    
    def get_state_config(state):
        if state.next == ():
            # Error, this state is not supposed to be initiated.
            logger.error(f"Thread {thread_id} has no next state, cannot stream.")
            return None
        if state.values["messages"] and state.values["messages"][-1].type != "human":
            # Error state, last message is not a HumanMessage.
            logger.error(f"Thread {thread_id} last message is not a HumanMessage, cannot stream.")
            return None
        if not state.metadata.get("user_id"):
            # Error state, no user_id in metadata.
            logger.error(f"Thread {thread_id} has no user_id in metadata, cannot stream.")
            return None
        config = {"configurable": {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "user_id": state.metadata.get("user_id")},
        }
        return config
    
    async def stream_generator():
        try:
            state = await graph.aget_state(config={"configurable": {"thread_id": thread_id}})
            config = get_state_config(state)
            if not config:
                yield "event: close\ndata: \n\n"
                return
            thoughts = []
            tokens = ""
            async for event in graph.astream_events(None, config=config):
                if thoughts == []:
                    thoughts.append("Thinking...")
                    yield f"event: thought\ndata: {thoughts[0]}\n\n"
                if thought := stream_thought(event):
                    thoughts.append(thought)
                    html_out = "<br>".join(thoughts)
                    yield f"event: thought\ndata: {orjson.dumps(html_out).decode()[1:-1]}\n\n"
                if token := stream_token(event):
                    tokens += token
                    yield f"event: chunk\ndata: {orjson.dumps(tokens).decode()[1:-1]}\n\n"
        except Exception as e:
            logger.error(f"STREAM GENERATOR ERROR: {e}")
        yield "event: close\ndata: \n\n"
        return
    return StreamingResponse(stream_generator(), media_type="text/event-stream")
        

app.include_router(main_router)
app.include_router(html_router)

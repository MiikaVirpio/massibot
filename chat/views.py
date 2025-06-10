from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from langgraph_sdk import get_sync_client
from langchain_core.messages import HumanMessage

from mem0 import Memory

from .models import Profile, Thread

def ensure_authenticated(func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            request.session.flush()  # Ensure session is emptied
            return HttpResponse("Unauthorized", status=401)
        return func(request, *args, **kwargs)
    return wrapper


@ensure_authenticated
def index(request):
    
    # LangGraph client
    client = get_sync_client(url=settings.BOT_URL, headers={"X-Master-Key": settings.BOT_MASTER_KEY})
    
    # Thread_id from session. Create new if it doesn't exist.
    if not request.session.get("bot_thread_id"):
        # Get user profile. Create new if it doesn't exist.
        try:
            profile = Profile.objects.get(user=request.user)
        except ObjectDoesNotExist:
            profile = Profile.objects.create(user=request.user)
        # Get latest thread. Create new if it doesn't exist.
        thread = profile.thread_set.last()
        if not thread:
            bot_thread = client.threads.create()
            thread = Thread.objects.create(profile=profile, bot_thread_id=bot_thread["thread_id"])
        # Set thread_id to session
        request.session["bot_thread_id"] = thread.bot_thread_id
    
    thread_id = request.session.get("bot_thread_id")
    
    # User id, hard coded for now
    user_id = request.session.get("user_id")
    
    # Messages from thread_state
    thread_state = client.threads.get_state(thread_id)
    messages = []
    if thread_state["values"]:
        for message in thread_state["values"]["messages"]:
            if message["type"] == "human":
               sender = "human"
            elif message["type"] == "ai":
                if message["content"] == "":
                    # Empty type ai messages are likely tool calls
                    continue
                sender = "bot"
            else:
                # Skip other message types
                continue
            
            # Replace every \n with <br>
            message_content = message["content"].replace("\n", "<br>")
            messages.append({"sender": sender, "content": message_content})

    context = {"user_id": user_id,  "messages": [render_to_string("chat/message.html", {"message": message}) for message in messages]}
    return render(request, "chat/index.html", context)

@ensure_authenticated
def send_message(request):
    user_message = request.POST.get("user-message")
    
    human_message = HumanMessage(content=user_message)
    
    # LangGraph client
    client = get_sync_client(url=settings.BOT_URL, headers={"X-Master-Key": settings.BOT_MASTER_KEY})
    
    thread_id = request.session.get("bot_thread_id")
    user_id = request.session.get("user_id")
    
    # Update thread state with user message to later stream response
    updated_state = client.threads.update_state(
        thread_id=thread_id,
        values={"messages": [human_message], "configurable": {"thread_id": thread_id, "user_id": user_id}},
        as_node="__start__",
    )
    checkpoint_id = updated_state["checkpoint_id"]
    
    
    # SSE Html url
    sse_url = f"{settings.BOT_URL}/sse-html2/{thread_id}/{checkpoint_id}"
    
    context = {
        "message": {"sender": "human", "content": user_message},
        "sse_url": sse_url,
    }
    return render(request, "chat/message.html", context)

@ensure_authenticated
def reset_thread(request):
    
    # Get user profile from request
    profile = Profile.objects.get(user=request.user)
    
    # LangGraph client
    client = get_sync_client(url=settings.BOT_URL, headers={"X-Master-Key": settings.BOT_MASTER_KEY})
    
    # Create new thread and set it to session
    bot_thread = client.threads.create()
    thread = Thread.objects.create(profile=profile, bot_thread_id=bot_thread["thread_id"])
    request.session["bot_thread_id"] = thread.bot_thread_id
    request.session["user_id"] = "finishup"
    
    # Redirect to index
    return redirect("chat:index")

@ensure_authenticated
def get_summary(request):
    # LangGraph client
    client = get_sync_client(url=settings.BOT_URL, headers={"X-Master-Key": settings.BOT_MASTER_KEY})
    
    # Get thread state
    thread_state = client.threads.get_state(request.session.get("bot_thread_id"))

    # Get summary from thread state
    summary = thread_state["values"].get("summary")
    if summary and summary.get("summary"):
        return HttpResponse(summary.get("summary"), content_type="text/plain")
    else:
        return HttpResponse("No summary yet. Get talking!", content_type="text/plain")

@ensure_authenticated
def get_memories(request):
    user_id = request.session.get("user_id")
    print(f"User ID: {user_id}")
    memtype = request.GET.get("memtype")
    print(f"Memory Type: {memtype}")
    # LangGraph client
    client = get_sync_client(url=settings.BOT_URL, headers={"X-Master-Key": settings.BOT_MASTER_KEY})
    
    formatted_memories = "No memories yet, make some!"
    # memory store from request parameters
    if memtype == "personal":
        memories = client.store.search_items(["personal", user_id])
        if memories and len(memories) > 0 and memories.get("items") and len(memories.get("items")) > 0:
            formatted_memories = "<br>".join([f"{key}: {str(value)}" for key, value in memories.get("items")[-1].get("value").get("content").items()])
        
    if memtype == "financial":
        memories = client.store.search_items(["financial", user_id])
        if memories and len(memories) > 0 and memories.get("items") and len(memories.get("items")) > 0:
            formatted_memories = "<br>".join([str(m.get("value").get("content")) for m in memories.get("items")])
    
    if memtype == "life":
        mem= Memory.from_config(settings.MEM0CONF)
        vector_memories = mem.vector_store.list({"user_id": user_id})
        if vector_memories and len(vector_memories) > 0 and vector_memories[0] and len(vector_memories[0]) > 0:
            formatted_memories = "<br>".join([str(m.payload.get("data")) for m in vector_memories[0] if hasattr(m, 'payload')])

    return HttpResponse(formatted_memories, content_type="text/plain")

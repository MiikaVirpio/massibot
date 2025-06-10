import os

from langgraph_sdk import Auth

"""
This file is used by the langgraph.json when launching the langgraph server.
"""

auth = Auth()
# Every request must have a very secret master key in "Authorization" header.
master_key = os.getenv("MASTER_KEY")
# Raise exception at initialization if master key is not set.
if not master_key:
    raise Exception("MASTER_KEY is not set in the environment variables.")

@auth.authenticate
async def authenticate(headers: dict) -> Auth.types.MinimalUserDict:
    # Try both string and bytes keys, and normalize for comparison
    key = headers.get("X-Master-Key") or headers.get("x-master-key") \
        or headers.get(b"X-Master-Key") or headers.get(b"x-master-key")
    # If key is bytes, decode to str
    if isinstance(key, bytes):
        key = key.decode()
    if key != master_key:
        raise Auth.exceptions.HTTPException(401, "Unauthorized")
    return {"identity": "admin"}

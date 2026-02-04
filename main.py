import os
import asyncio
from mem0 import Memory
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# configuration for memory client
config = {
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
            "api_key": os.getenv("OPENAI_API_KEY")
        }
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-5-mini",
            "api_key": os.getenv("OPENAI_API_KEY")
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": os.getenv("QDRANT_HOST"),
            "port": 6333,
        },
    },
    "graph_store" : {
        "provider" : "neo4j",
        "config": {
            "url": os.getenv("NEO4J_URL"), 
            "username": os.getenv("NEO4J_USERNAME"), 
            "password": os.getenv("NEO4J_PASSWORD")
        },
    }
}

mem_client = Memory.from_config(config)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# short-term memory 
stm = []
# rolling summary
mtm = ''

# llm to create rolling summary
async def rolling_summary():
    
    global stm, mtm
    
    if(len(stm) < 5):
        return
    
    contents = "\n\n\n".join([f'user : {m.get("user")} assistant : {m.get("assistant")}'  for m in stm])  
    SYSTEM_PROMPT = f'''
        you are a chat summarizer
        summarize the conversations between user and assistant so far for future interactions
        
        Rules: 
        - Preserve user goals and intent
        - Preserve decisions and constraints
        - Preserve unresolved questions
        - Remove examples and repetition
        - Be concise and factual
    '''
    
    messages = [
        {"role" : "system" , "content" : SYSTEM_PROMPT},
        {"role" : "user" , "content" : contents}
    ]
    
    response = await client.responses.create(
        model = "gpt-5-mini",
        input = messages
    )
    
    summary = response.output_text.strip()
    stm.clear()  # remove old entries
    mtm = summary

#  llm to decide if memory needs to be stored
async def memory_gate(user):
    prompt = f"""
    Decide if this conversation contains long-term user info.
    Reply YES if the user reveals:
    - name
    - role
    - preference
    - project
    - goal
    - background
    Reply only YES or NO.

    User: {user}
    """
    r = await client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )
    decision = r.output_text.strip().upper()
    print("[MEMORY GATE]:", decision)
    return "YES" in decision

# llm to extract memory from the response
async def extract_memory(user : str, assistant: str) -> str:
    prompt = f"""
       Extract ONLY long-term factual memory worth storing.
       Rules:
        - No explanations or opinions
        - No duplication
        - Max 1 sentence
        - If nothing worth storing, return NONE

        Conversation:
        User: {user}
        Assistant: {assistant}
    """
    res = await client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )
    text = res.output_text.strip()
    return None if text == "NONE" else text

# async function to store memory
async def store_memory_async(user, assistant, user_id="P101"):
    try:
        # extract memory
        memory = await extract_memory(user, assistant)
        if memory:
            mem_client.add(memory, user_id=user_id)
            
    except Exception as e:
        print(f"[ Async Memory Error]: {e}")


async def get_memories(message : str, user_id : str = "P101"):
    try:
        loop = asyncio.get_running_loop()
        mem_result = await loop.run_in_executor(
            None,
            lambda: mem_client.search(message, user_id=user_id)
        )
        memories = [m["memory"] for m in mem_result.get('results', [])]
        return memories
    except Exception as e:
        print(f"[ Get Memories Error]: {e}")
        return []   

async def chat(message: str, user_id: str = "P101"):

    memories_task = asyncio.create_task(get_memories(message, user_id))

    SYSTEM_PROMPT = """
    You are an AI assistant that provides accurate and concise information.
    Use provided memories if they are helpful.
    """
    recent_chats = "\n\n".join(
        [f"User: {m['user']}\nAssistant: {m['assistant']}" for m in stm]
    )

    memories = await memories_task

    context = "\n- ".join(memories) if memories else "None"

    # Build final prompt
    USER_PROMPT = f"""
    Query: {message}
    Rolling Summary: {mtm}
    Recent chats: {recent_chats}
    Context: {context}
    """

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT}
    ]

    # Start streaming response
    full_answer = ""

    async with client.responses.stream(
        model="gpt-5-mini",
        input=messages
    ) as stream:

        async for event in stream:
            if event.type == "response.output_text.delta":
                token = event.delta
                full_answer += token
                yield token  

    # Update short-term memory
    stm.append({"user": message, "assistant": full_answer})
    print(f"[STM Updated] Total Entries: {len(stm)}")
    print(f"mtm: {mtm}")

    # Background jobs (do NOT block user)
    asyncio.create_task(rolling_summary())
    asyncio.create_task(store_memory_async(message, full_answer, user_id))


async def main():

    while True:
        message = input(">> ")
        async for token in chat(message):
            print(token, end="", flush=True)
        print()

if __name__ == "__main__":
    asyncio.run(main())

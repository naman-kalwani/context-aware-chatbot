import os
import asyncio
from mem0 import Memory
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

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

async def store_memory_async(user, assistant, user_id="P101"):
    try:
        memory = await extract_memory(user, assistant)
        if memory:
            mem_client.add(memory, user_id=user_id)
    except Exception as e:
        print(f"[ Async Memory Error]: {e}")

# main chat function
async def chat(message : str, user_id : str = "P101") -> str:
    
    loop = asyncio.get_running_loop()
    mem_result = await loop.run_in_executor(
        None,
        lambda: mem_client.search(message, user_id=user_id)
    )
    
    memories = [m["memory"] for m in mem_result.get('results', [])]
    context = "\n- ".join(memories) if memories else "None"
    # print(f"Context used: {context}")
    
    SYSTEM_PROMPT = f"""
        -You are an AI assistant that provides accurate and concise information based on user queries 
    """
    USER_PROMPT = f"""
        Query : {message}  
        Context : {context}   
    """
    messages = [
        {'role' : 'system' , 'content' : SYSTEM_PROMPT},
        {"role" : "user" , "content" : USER_PROMPT}
    ]
    response = await client.responses.create(
        model="gpt-5-mini",
        input=messages
    )
    messages.append(
        {"role" : "assistant" , "content" : response.output_text}
    )
    
    # we are calling another LLM to extract memory from the response
    asyncio.create_task(
        store_memory_async(message, response.output_text, user_id=user_id)
    )
    
    return response.output_text

# async def main():
#     while True:
#         message = input(">> ")
#         print(await chat(message))

# if __name__ == "__main__":
#     asyncio.run(main())

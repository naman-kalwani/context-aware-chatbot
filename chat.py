from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from main import chat

app = FastAPI(title="Memory Chatbot API")

class ChatRequest(BaseModel):
  message: str
  user_id: str = "P101"
  
class ChatResponse(BaseModel):
  response: str

@app.get("/")
async def read_root():
  return {"message": "Welcome to the Memory Chatbot API"}

@app.post("/chat/" , response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
  async def token_generator():
    async for token in chat(request.message, request.user_id):
      yield token

  return StreamingResponse(
    token_generator(),
    media_type="text/plain"
  )

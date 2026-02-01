from fastapi import FastAPI
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
  response_text = await chat(request.message , request.user_id)
  return ChatResponse(response=response_text)

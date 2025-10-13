from fastapi import FastAPI
from backend.app.api.endpoints import documents
from backend.app.api.endpoints import chat # <-- IMPORT THE NEW ROUTER

app = FastAPI(title="Intelligent Learning Assistant")

# Include the routers
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(chat.router, prefix="/chat", tags=["chat"]) # <-- ADD THE CHAT ROUTER

@app.get("/")
def read_root():
    return {"message": "Welcome to the Intelligent Learning Assistant API"}
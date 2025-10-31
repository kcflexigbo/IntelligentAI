from fastapi import FastAPI
from app.api.endpoints import documents
# from app.api.endpoints import chat # <-- REMOVE THIS LINE
from app.api.endpoints import auth
from app.api.endpoints import conversations # <-- ADD THIS LINE
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ContextIQ")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(documents.router, prefix="/documents", tags=["documents"])
# app.include_router(chat.router, prefix="/chat", tags=["chat"]) # <-- REMOVE THIS LINE
app.include_router(conversations.router, prefix="/conversations", tags=["conversations"]) # <-- ADD THIS LINE
app.include_router(auth.router, prefix="/auth", tags=["auth"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the ContextIQ API"}
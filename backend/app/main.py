from fastapi import FastAPI
from app.api.endpoints import documents
from app.api.endpoints import chat
from app.api.endpoints import auth
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Intelligent Learning Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Include the routers
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Intelligent Learning Assistant API"}
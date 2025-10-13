# backend/app/main.py
from fastapi import FastAPI
from app.api.endpoints import documents  # Import the new router

app = FastAPI(title="Intelligent Learning Assistant")

# Include the documents router
# All routes defined in documents.py will be available under the /documents prefix
app.include_router(documents.router, prefix="/documents", tags=["documents"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Intelligent Learning Assistant API"}

# Add other routers for auth, chat, etc. here in the future
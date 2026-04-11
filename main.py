import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.sentence_router import router as sentence_router
from db.connection import engine
from db.models import Base

load_dotenv()

app = FastAPI(
    title="IELTS Assistant",
    description="AI-powered IELTS writing coach — sentence correction API.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create all tables on startup (safe to run multiple times).
Base.metadata.create_all(bind=engine)

# Register routers.
app.include_router(sentence_router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "1") == "1",
    )

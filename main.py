import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth_router import router as auth_router
from api.profile_router import router as profile_router
from api.sentence_router import router as sentence_router
from api.speech_router import router as speech_router
from api.user_router import router as user_router
from api.youtube_router import router as youtube_router

load_dotenv()

app = FastAPI(
    title="IELTS Assistant",
    description="AI-powered IELTS coach — writing correction and speaking practice API.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers.
app.include_router(sentence_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(user_router)
app.include_router(youtube_router)
app.include_router(speech_router)

# Shadowing disabled — feature unused (audio upload + Whisper; not suitable for Vercel).
# from api.shadowing_router import router as shadowing_router
# app.include_router(shadowing_router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "1") == "1",
    )

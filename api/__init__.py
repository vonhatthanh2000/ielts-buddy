from api.auth_router import router as auth_router
from api.profile_router import router as profile_router
from api.sentence_router import router as sentence_router
from api.user_router import router as user_router

__all__ = ["auth_router", "profile_router", "sentence_router", "user_router"]

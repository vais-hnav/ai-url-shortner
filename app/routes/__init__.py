from app.routes.ai_routes import router as ai_router
from app.routes.auth_routes import router as auth_router
from app.routes.url_routes import router as url_router

__all__ = ["url_router", "auth_router", "ai_router"]

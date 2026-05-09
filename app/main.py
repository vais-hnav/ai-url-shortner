# Create FastAPI application instance
# Add health check route
from fastapi import FastAPI

from app.routes import auth_router, url_router

app = FastAPI()

app.include_router(auth_router)
app.include_router(url_router)

@app.get("/")
def health_check():
    return {"status": "ok"}

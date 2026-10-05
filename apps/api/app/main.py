from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import public_router, router
from app.config import get_settings


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", docs_url="/docs" if settings.app_env != "production" else None)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(public_router)
app.include_router(router)


"""EntryPoint — Global Visa AI Assistant Backend

FastAPI application that routes all API calls through to Supabase
and handles AI analysis via PaddleOCR + Gemma on AMD MI300X.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config.settings import settings
from backend.services.gemma_service import DeepSeekServiceError
from backend.routes.auth import router as auth_router
from backend.routes.reference import router as reference_router
from backend.routes.applications import router as applications_router
from backend.routes.documents import router as documents_router
from backend.routes.analysis import router as analysis_router
from backend.routes.queries import router as queries_router
from backend.routes.queries import admin_router as queries_admin_router
from backend.routes.admin import router as admin_router

app = FastAPI(
    title="EntryPoint Visa AI Assistant",
    description="Global visa application AI assistant backend",
    version="1.0.0",
)

logger = logging.getLogger("entrypoint")


@app.exception_handler(DeepSeekServiceError)
async def deepseek_error_handler(request: Request, exc: DeepSeekServiceError):
    """Return provider failures as readable API errors for the frontend."""
    logger.error("DeepSeek request failed for %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=502,
        content={"detail": str(exc), "provider": "fireworks"},
    )

# CORS — allow frontend preview URLs and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(reference_router)
app.include_router(applications_router)
app.include_router(documents_router)
app.include_router(analysis_router)
app.include_router(queries_router)
app.include_router(queries_admin_router)
app.include_router(admin_router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host=settings.host, port=settings.port, reload=True)

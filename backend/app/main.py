"""
FastAPI Application - Invoice Processor
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
from datetime import datetime

from app.config import settings, configure_for_environment
from app.utils.logger import setup_logging, get_logger
from app.models import HealthCheck

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Configure for environment
configure_for_environment()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events para FastAPI
    """
    # Startup
    logger.info("=" * 80)
    logger.info(f"🚀 Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"   Ambiente: {settings.ENVIRONMENT}")
    logger.info(f"   Debug: {settings.DEBUG}")
    logger.info("=" * 80)
    
    # TODO: Inicializar servicios
    # - Scheduler para Google Drive
    # - Conexión a Supabase
    # - Workers de procesamiento
    
    yield
    
    # Shutdown
    logger.info("=" * 80)
    logger.info("🛑 Apagando aplicación...")
    logger.info("=" * 80)
    
    # TODO: Cleanup
    # - Detener scheduler
    # - Cerrar conexiones
    # - Limpiar archivos temporales


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de procesamiento automatizado de facturas mediante IA",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request, call_next):
    """
    Agregar header con tiempo de procesamiento
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Handler global para excepciones no manejadas
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """
    Endpoint raíz
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else None,
        "health": "/health"
    }


@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check():
    """
    Health check endpoint
    """
    # TODO: Verificar estado de servicios
    # - Supabase connection
    # - Claude API (rate limit status)
    # - Google Drive API
    # - Worker status
    
    return HealthCheck(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(),
        services={
            "supabase": True,  # TODO: check real status
            "claude_api": True,
            "google_drive": True,
            "workers": True
        }
    )


# ============================================================================
# API ROUTERS
# ============================================================================

# API ROUTERS
from app.routers import invoices

app.include_router(invoices.router, prefix=f"{settings.API_PREFIX}/invoices", tags=["Invoices"])

# app.include_router(invoices.router, prefix=f"{settings.API_PREFIX}/invoices", tags=["Invoices"])
# app.include_router(vendors.router, prefix=f"{settings.API_PREFIX}/vendors", tags=["Vendors"])
# app.include_router(stores.router, prefix=f"{settings.API_PREFIX}/stores", tags=["Stores"])
# app.include_router(products.router, prefix=f"{settings.API_PREFIX}/products", tags=["Products"])
# app.include_router(queue.router, prefix=f"{settings.API_PREFIX}/queue", tags=["Queue"])
# app.include_router(dashboard.router, prefix=f"{settings.API_PREFIX}/dashboard", tags=["Dashboard"])


# ============================================================================
# STARTUP MESSAGE
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🔥 Iniciando servidor de desarrollo...")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
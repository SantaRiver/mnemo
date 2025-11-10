"""FastAPI application entry point."""

import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from nlp_service import __version__
from nlp_service.api import metrics
from nlp_service.api.dependencies import get_analyzer, get_container
from nlp_service.api.logging_config import configure_logging, get_logger
from nlp_service.api.schemas import AnalyzeRequest, HealthResponse, StatsResponse
from nlp_service.config.settings import get_settings
from nlp_service.core.analyzer import TextAnalyzer
from nlp_service.domain.models import AnalysisResult


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup/shutdown events.
    
    Args:
        app: FastAPI application
        
    Yields:
        None
    """
    # Startup
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)
    logger.info("starting_nlp_service", version=__version__)
    
    yield
    
    # Shutdown
    logger.info("shutting_down_nlp_service")


# Create FastAPI app
app = FastAPI(
    title="NLP Service",
    description="Service for analyzing diary entries and extracting actions",
    version=__version__,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logger
logger = get_logger(__name__)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Any) -> Response:
    """Middleware to track request time and metrics.
    
    Args:
        request: HTTP request
        call_next: Next middleware
        
    Returns:
        HTTP response
    """
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Process-Time"] = str(process_time)
        
        # Record metrics
        if get_settings().metrics_enabled:
            metrics.request_latency.observe(process_time)
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            "request_failed",
            error=str(e),
            path=request.url.path,
            duration=process_time
        )
        raise


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.
    
    Returns:
        Health status
    """
    return HealthResponse(status="ok", version=__version__)


@app.post("/api/v1/analyze", response_model=AnalysisResult)
async def analyze_text(
    request: AnalyzeRequest,
    analyzer: TextAnalyzer = Depends(get_analyzer)
) -> AnalysisResult:
    """Analyze text and extract actions.
    
    Args:
        request: Analysis request
        analyzer: Text analyzer dependency
        
    Returns:
        Analysis result with extracted actions
        
    Raises:
        HTTPException: If analysis fails
    """
    start_time = time.time()
    settings = get_settings()
    
    try:
        # Record request metric
        if settings.metrics_enabled:
            metrics.requests_total.labels(user_id=str(request.user_id)).inc()
        
        # Log request (without full text for privacy)
        logger.info(
            "analyze_request",
            user_id=request.user_id,
            text_length=len(request.text),
            date=str(request.date)
        )
        
        # Perform analysis
        result = await analyzer.analyze_text(
            user_id=request.user_id,
            text=request.text,
            analysis_date=request.date
        )
        
        # Record metrics
        if settings.metrics_enabled:
            metrics.requests_success.inc()
            metrics.actions_extracted.observe(len(result.actions))
            
            if result.meta.used_llm:
                metrics.llm_calls_total.inc()
                if result.meta.llm_latency_ms:
                    metrics.llm_latency.observe(result.meta.llm_latency_ms / 1000.0)
            
            if result.meta.heuristic_latency_ms:
                metrics.heuristic_latency.observe(result.meta.heuristic_latency_ms / 1000.0)
        
        # Log result
        duration = time.time() - start_time
        logger.info(
            "analyze_success",
            user_id=request.user_id,
            actions_count=len(result.actions),
            used_llm=result.meta.used_llm,
            duration=duration
        )
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        
        # Record error metrics
        if settings.metrics_enabled:
            metrics.requests_failed.labels(error_type=type(e).__name__).inc()
        
        # Log error
        logger.error(
            "analyze_failed",
            user_id=request.user_id,
            error=str(e),
            error_type=type(e).__name__,
            duration=duration
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@app.get("/api/v1/stats/{user_id}", response_model=StatsResponse)
async def get_user_stats(user_id: int) -> StatsResponse:
    """Get user statistics.
    
    Args:
        user_id: User ID
        
    Returns:
        User statistics
    """
    try:
        container = get_container()
        analyzer = container.get_analyzer()
        
        stats = analyzer.history_service.get_user_stats(user_id)
        
        return StatsResponse(
            user_id=user_id,
            total_templates=stats["total_templates"],
            total_actions=stats["total_actions"]
        )
        
    except Exception as e:
        logger.error("stats_failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )


@app.get("/metrics")
async def get_metrics() -> Response:
    """Prometheus metrics endpoint.
    
    Returns:
        Prometheus metrics in text format
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.delete("/api/v1/cache")
async def clear_cache() -> dict[str, str]:
    """Clear cache (for testing/admin purposes).
    
    Returns:
        Success message
    """
    try:
        container = get_container()
        analyzer = container.get_analyzer()
        
        if analyzer.cache_service:
            # Only works with InMemoryCacheService
            if hasattr(analyzer.cache_service, 'clear'):
                analyzer.cache_service.clear()
                return {"status": "success", "message": "Cache cleared"}
        
        return {"status": "info", "message": "Cache not available or not clearable"}
        
    except Exception as e:
        logger.error("cache_clear_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "nlp_service.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

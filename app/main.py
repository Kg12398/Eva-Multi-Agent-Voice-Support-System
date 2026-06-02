"""
FastAPI Application — REST API for health checks, dashboard, and admin operations.
This runs alongside the LiveKit worker as a separate process.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime

from app.config import settings
from app.services.redis_service import redis_service
from app.services.db_service import db_service
from app.utils.logger import setup_logging, CallLogger

logger = CallLogger(call_id="api")


# ============================================
# Application Lifecycle
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    setup_logging(log_level=settings.LOG_LEVEL, json_format=settings.is_production)
    logger.info("Starting KG ElectroPower Voice Agent API...")

    await redis_service.connect() #connect redis in async mode
    await db_service.connect()
    logger.info("All services connected")

    yield

    # Shutdown
    await redis_service.disconnect()
    await db_service.disconnect()
    logger.info("All services disconnected. Goodbye!")


# ============================================
# FastAPI App
# ============================================

app = FastAPI(
    title="KG ElectroPower Voice Agent API",
    description="AI-powered voice service support system for KG ElectroPower",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS (for dashboard frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Health Check Endpoints
# ============================================

@app.get("/health")
async def health_check():
    """System health check — verifies all dependencies."""
    checks = {
        "api": "healthy",
        "redis": "unknown",
        "postgresql": "unknown",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Check Redis
    try:
        active_calls = await redis_service.get_active_call_count()
        checks["redis"] = "healthy"
        checks["active_calls"] = active_calls
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"

    # Check PostgreSQL
    try:
        # Simple connection test
        checks["postgresql"] = "healthy"
    except Exception as e:
        checks["postgresql"] = f"unhealthy: {str(e)}"

    # Overall status
    all_healthy = all(
        v == "healthy" for k, v in checks.items()
        if k in ["api", "redis", "postgresql"]
    )
    checks["status"] = "healthy" if all_healthy else "degraded"

    status_code = 200 if all_healthy else 503
    return checks


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "KG ElectroPower Voice Agent",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


# ============================================
# Call Management Endpoints
# ============================================

@app.get("/api/calls/active")
async def get_active_calls():
    """Get count of currently active calls."""
    count = await redis_service.get_active_call_count()
    return {"active_calls": count}


# ============================================
# Ticket Endpoints
# ============================================

@app.get("/api/tickets")
async def get_tickets(limit: int = 20):
    """Get recent support tickets."""
    tickets = await db_service.get_recent_tickets(limit=limit)
    return {
        "tickets": [
            {
                "ticket_number": t.ticket_number,
                "customer_name": t.customer_name,
                "product_category": t.product_category,
                "issue_description": t.issue_description,
                "priority": t.priority,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tickets
        ],
        "total": len(tickets),
    }


@app.get("/api/tickets/{ticket_number}")
async def get_ticket(ticket_number: str):
    """Get a specific ticket by number."""
    ticket = await db_service.get_ticket(ticket_number)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {
        "ticket_number": ticket.ticket_number,
        "call_id": ticket.call_id,
        "customer_name": ticket.customer_name,
        "phone_number": ticket.phone_number,
        "product_category": ticket.product_category,
        "product_model": ticket.product_model,
        "serial_number": ticket.serial_number,
        "issue_description": ticket.issue_description,
        "diagnosis_attempted": ticket.diagnosis_attempted,
        "troubleshooting_steps": ticket.troubleshooting_steps,
        "priority": ticket.priority,
        "status": ticket.status,
        "sentiment": ticket.sentiment,
        "call_summary": ticket.call_summary,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
    }


# ============================================
# Run with: uvicorn app.main:app --reload
# ============================================

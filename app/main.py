import time
import uuid
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Literal, List

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Query,
    Depends,
    Header,
    Path,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings
from app.services.redis_service import redis_service
from app.services.db_service import db_service
from app.utils.logger import setup_logging, CallLogger


logger = CallLogger(call_id="api")


# Response Schemas

class RootResponse(BaseModel):
    service: str
    version: str
    status: str
    docs: Optional[str]


class ActiveCallsResponse(BaseModel):
    active_calls: int


class TicketListItem(BaseModel):
    ticket_number: str
    customer_name: Optional[str]
    product_category: Optional[str]
    issue_description: Optional[str]
    priority: Optional[str]
    status: Optional[str]
    created_at: Optional[str]


class TicketListResponse(BaseModel):
    tickets: List[TicketListItem]
    total: int


class TicketDetailResponse(BaseModel):
    ticket_number: str
    call_id: Optional[str]
    customer_name: Optional[str]
    phone_number: Optional[str]
    product_category: Optional[str]
    product_model: Optional[str]
    serial_number: Optional[str]
    issue_description: Optional[str]
    diagnosis_attempted: Optional[str]
    troubleshooting_steps: Optional[str]
    priority: Optional[str]
    status: Optional[str]
    sentiment: Optional[str]
    call_summary: Optional[str]
    created_at: Optional[str]


class AuthContext(BaseModel):
    role: Literal["admin", "subscriber"]
    subscriber_id: Optional[str] = None


# Helper Functions

def utc_now_iso() -> str:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def serialize_datetime(value) -> Optional[str]:
    """Safely convert datetime to ISO string."""
    return value.isoformat() if value else None


def hide_error_detail(error: Exception) -> str:
    """
    Do not expose internal exception text in production.
    In local/dev, allow details for easier debugging.
    """
    if settings.is_production:
        return "unhealthy"
    return f"unhealthy: {str(error)}"


# Application Lifecycle

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""

    setup_logging(
        log_level=settings.LOG_LEVEL,
        json_format=settings.is_production,
    )

    logger.info("Starting KG ElectroPower Voice Agent API...")

    # Production safety checks
    if settings.is_production:
        if not getattr(settings, "API_KEY", None):
            raise RuntimeError("API_KEY must be configured in production")

        if not getattr(settings, "ALLOWED_ORIGINS", None):
            raise RuntimeError("ALLOWED_ORIGINS must be configured in production")

    # Connect Redis
    try:
        await redis_service.connect()
        logger.info("Redis connected")
    except Exception as e:
        logger.error(f"Failed to connect to Redis on startup: {e}", exc_info=True)
        raise

    # Connect PostgreSQL
    try:
        await db_service.connect()
        logger.info("PostgreSQL connected")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL on startup: {e}", exc_info=True)

        try:
            await redis_service.disconnect()
        except Exception as redis_error:
            logger.error(
                f"Redis cleanup failed after DB startup failure: {redis_error}",
                exc_info=True,
            )

        raise

    logger.info("All services connected")

    yield

    # Shutdown
    try:
        await redis_service.disconnect()
        logger.info("Redis disconnected")
    except Exception as e:
        logger.error(f"Error disconnecting Redis: {e}", exc_info=True)

    try:
        await db_service.disconnect()
        logger.info("PostgreSQL disconnected")
    except Exception as e:
        logger.error(f"Error disconnecting PostgreSQL: {e}", exc_info=True)

    logger.info("All services disconnected. Goodbye!")



# FastAPI App

app = FastAPI(
    title="KG ElectroPower Voice Agent API",
    description="AI-powered voice service support system for KG ElectroPower",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)


# CORS

app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "ALLOWED_ORIGINS", []),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-API-Key",
        "X-Subscriber-ID",
        "X-User-Role",
    ],
)


# Middleware: Request ID + Logging + Security Headers

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """
    Adds request ID, measures request time, logs request result,
    and attaches basic security headers.
    """

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            f"[{request_id}] {request.method} {request.url.path} "
            f"failed after {duration_ms:.1f}ms: {exc}",
            exc_info=True,
        )
        raise

    duration_ms = (time.perf_counter() - start_time) * 1000

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"

    logger.info(
        f"[{request_id}] {request.method} {request.url.path} "
        f"-> {response.status_code} in {duration_ms:.1f}ms"
    )

    return response
# Global Exception Handlers


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Consistent error response for expected HTTP errors."""

    request_id = getattr(request.state, "request_id", None)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Safe response for unexpected errors."""

    request_id = getattr(request.state, "request_id", None)

    logger.error(
        f"[{request_id}] Unhandled exception: {exc}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request_id,
        },
    )


# Auth Dependency

async def verify_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    x_user_role: Optional[str] = Header(default="subscriber", alias="X-User-Role"),
    x_subscriber_id: Optional[str] = Header(default=None, alias="X-Subscriber-ID"),
) -> AuthContext:
    """
    Internal API-key protection.

    For production SaaS, JWT/OAuth should replace this.
    This version is acceptable for internal services, dashboard testing,
    and controlled environments.
    """

    expected_key = getattr(settings, "API_KEY", None)

    if not expected_key:
        if settings.is_production:
            raise HTTPException(
                status_code=500,
                detail="API key is not configured",
            )

        # Local development only
        return AuthContext(
            role="admin",
            subscriber_id=x_subscriber_id,
        )

    if not x_api_key or not secrets.compare_digest(x_api_key, expected_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )

    role = x_user_role.lower().strip() if x_user_role else "subscriber"

    if role not in ["admin", "subscriber"]:
        raise HTTPException(
            status_code=403,
            detail="Invalid user role",
        )

    if role == "subscriber" and not x_subscriber_id:
        raise HTTPException(
            status_code=400,
            detail="X-Subscriber-ID header is required for subscriber access",
        )

    return AuthContext(
        role=role,
        subscriber_id=x_subscriber_id,
    )


# Health Check Endpoints

@app.get("/health")
async def health_check():
    """System health check — verifies API, Redis, and PostgreSQL."""

    checks = {
        "api": "healthy",
        "redis": "unknown",
        "postgresql": "unknown",
        "timestamp": utc_now_iso(),
    }

    # Redis health check
    try:
        active_calls = await redis_service.get_active_call_count()
        checks["redis"] = "healthy"
        checks["active_calls"] = active_calls
    except Exception as e:
        logger.error(f"Redis health check failed: {e}", exc_info=True)
        checks["redis"] = hide_error_detail(e)

    # PostgreSQL health check
    try:
        if hasattr(db_service, "ping"):
            await db_service.ping()
        elif hasattr(db_service, "execute"):
            await db_service.execute("SELECT 1")
        else:
            raise RuntimeError("db_service must expose ping() or execute()")

        checks["postgresql"] = "healthy"

    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}", exc_info=True)
        checks["postgresql"] = hide_error_detail(e)

    all_healthy = (
        checks["api"] == "healthy"
        and checks["redis"] == "healthy"
        and checks["postgresql"] == "healthy"
    )

    checks["status"] = "healthy" if all_healthy else "degraded"

    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content=checks,
    )


@app.get("/", response_model=RootResponse)
async def root():
    """Root endpoint."""

    return RootResponse(
        service="KG ElectroPower Voice Agent",
        version="1.0.0",
        status="running",
        docs="/docs" if not settings.is_production else None,
    )


# Call Management Endpoints

@app.get("/api/calls/active", response_model=ActiveCallsResponse)
async def get_active_calls(
    auth: AuthContext = Depends(verify_api_key),
):
    """Get count of currently active calls."""

    try:
        # For future improvement:
        # If Redis service supports tenant-level active calls,
        # use auth.subscriber_id for subscriber users.
        count = await redis_service.get_active_call_count()

    except Exception as e:
        logger.error(
            f"Failed to fetch active call count: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve active call data",
        )

    return ActiveCallsResponse(active_calls=count)

# Ticket Endpoints

@app.get("/api/tickets", response_model=TicketListResponse)
async def get_tickets(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of tickets to return",
    ),
    auth: AuthContext = Depends(verify_api_key),
):
    """Get recent support tickets."""

    try:
        # Production tenant isolation:
        # - admin can see all tickets
        # - subscriber can only see own tickets
        if auth.role == "admin":
            tickets = await db_service.get_recent_tickets(limit=limit)
        else:
            tickets = await db_service.get_recent_tickets(
                limit=limit,
                subscriber_id=auth.subscriber_id,
            )

    except TypeError:
        raise HTTPException(
            status_code=500,
            detail=(
                "db_service.get_recent_tickets must support "
                "subscriber_id for tenant isolation"
            ),
        )

    except Exception as e:
        logger.error(
            f"Failed to fetch recent tickets: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve tickets",
        )

    return TicketListResponse(
        tickets=[
            TicketListItem(
                ticket_number=t.ticket_number,
                customer_name=t.customer_name,
                product_category=t.product_category,
                issue_description=t.issue_description,
                priority=t.priority,
                status=t.status,
                created_at=serialize_datetime(t.created_at),
            )
            for t in tickets
        ],
        total=len(tickets),
    )


@app.get("/api/tickets/{ticket_number}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_number: str = Path(
        ...,
        min_length=3,
        max_length=50,
        description="Unique ticket number",
    ),
    auth: AuthContext = Depends(verify_api_key),
):
    """Get a specific ticket by ticket number."""

    try:
        # Production tenant isolation:
        # - admin can fetch any ticket
        # - subscriber can fetch only own ticket
        if auth.role == "admin":
            ticket = await db_service.get_ticket(ticket_number)
        else:
            ticket = await db_service.get_ticket(
                ticket_number,
                subscriber_id=auth.subscriber_id,
            )

    except TypeError:
        raise HTTPException(
            status_code=500,
            detail=(
                "db_service.get_ticket must support "
                "subscriber_id for tenant isolation"
            ),
        )

    except Exception as e:
        logger.error(
            f"Failed to fetch ticket {ticket_number}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve ticket",
        )

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    return TicketDetailResponse(
        ticket_number=ticket.ticket_number,
        call_id=ticket.call_id,
        customer_name=ticket.customer_name,
        phone_number=ticket.phone_number,
        product_category=ticket.product_category,
        product_model=ticket.product_model,
        serial_number=ticket.serial_number,
        issue_description=ticket.issue_description,
        diagnosis_attempted=ticket.diagnosis_attempted,
        troubleshooting_steps=ticket.troubleshooting_steps,
        priority=ticket.priority,
        status=ticket.status,
        sentiment=ticket.sentiment,
        call_summary=ticket.call_summary,
        created_at=serialize_datetime(ticket.created_at),
    )

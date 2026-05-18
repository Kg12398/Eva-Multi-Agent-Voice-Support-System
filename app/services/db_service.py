"""
Database service for PostgreSQL operations.
Handles persistent storage of call records, tickets, and knowledge documents.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.database_models import Base, CallRecord, Ticket, KnowledgeDocument
from app.models.call_state import CallSession
from app.models.agent_contracts import TicketCreate
from app.config import settings
from app.utils.logger import CallLogger

logger = CallLogger(call_id="database")


class DatabaseService:
    """Manages PostgreSQL operations for persistent data storage."""

    def __init__(self):
        self._engine = None
        self._session_factory = None
        self.is_connected = False

    async def connect(self):
        """Initialize database engine and create tables."""
        try:
            self._engine = create_async_engine(
                settings.DATABASE_URL,
                echo=False,
                pool_size=5,
                max_overflow=10,
            )
            self._session_factory = async_sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False
            )

            # Create tables if they don't exist
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self.is_connected = True
            logger.info("PostgreSQL connected and tables created")
        except Exception as e:
            self.is_connected = False
            logger.warning(f"PostgreSQL connection failed: {e}. Running in memory-only mode (No DB persistence).")


    async def disconnect(self):
        """Close database engine."""
        if self._engine:
            await self._engine.dispose()
            logger.info("PostgreSQL disconnected")

    def _get_session(self) -> AsyncSession:
        if not self.is_connected or not self._session_factory:
            raise RuntimeError("Database not connected. Please ensure PostgreSQL is running.")
        return self._session_factory()

    # ------ Call Records ------

    async def save_call_record(self, session: CallSession) -> str:
        """Save a completed call to the database."""
        if not self.is_connected:
            logger.warning(f"Database not connected. Skipping call record save for {session.call_id}")
            return "mock_record_id"

        async with self._get_session() as db:
            record = CallRecord(
                call_id=session.call_id,
                customer_name=session.slots.customer_name,
                phone_number=session.phone_number,
                contact_number=session.slots.contact_number,
                product_category=session.slots.product_category,
                product_model=session.slots.product_model,
                serial_number=session.slots.serial_number,
                city=session.slots.city,
                error_code=session.slots.error_code,
                issue_description=session.slots.issue_description,
                warranty_status=session.warranty_status,
                diagnosis_result=session.diagnosis_result,
                resolution_status=session.resolution_status,
                sentiment=session.sentiment.value if hasattr(session.sentiment, 'value') else session.sentiment,
                turn_count=session.turn_count,
                transcript=[msg.model_dump() for msg in session.conversation_history],
                ticket_id=session.ticket_id,
                created_at=session.created_at,
                ended_at=datetime.utcnow(),
            )
            db.add(record)
            await db.commit()
            logger.info(f"Call record saved: {session.call_id}")
            return record.id

    # ------ Tickets ------

    async def create_ticket(self, ticket_data: TicketCreate) -> str:
        """Create a support ticket and return the ticket number."""
        ticket_number = f"KGE-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        if not self.is_connected:
            logger.warning(f"Database not connected. Ticket {ticket_number} created in memory only.")
            return ticket_number

        async with self._get_session() as db:
            ticket = Ticket(
                ticket_number=ticket_number,
                call_id=ticket_data.call_id,
                customer_name=ticket_data.customer_name,
                phone_number=ticket_data.phone_number,
                contact_number=ticket_data.contact_number,
                product_category=ticket_data.product_category,
                product_model=ticket_data.product_model,
                serial_number=ticket_data.serial_number,
                city=ticket_data.city,
                error_code=ticket_data.error_code,
                issue_description=ticket_data.issue_description,
                diagnosis_attempted=ticket_data.diagnosis_attempted,
                troubleshooting_steps=ticket_data.troubleshooting_steps,
                priority=ticket_data.priority,
                sentiment=ticket_data.sentiment,
                call_summary=ticket_data.call_summary,
            )
            db.add(ticket)
            await db.commit()
            logger.info(f"Ticket created: {ticket_number}")
            return ticket_number

    async def get_ticket(self, ticket_number: str) -> Optional[Ticket]:
        """Retrieve a ticket by its number."""
        async with self._get_session() as db:
            result = await db.execute(
                select(Ticket).where(Ticket.ticket_number == ticket_number)
            )
            return result.scalar_one_or_none()

    async def get_recent_tickets(self, limit: int = 20) -> List[Ticket]:
        """Get recent tickets for the dashboard."""
        async with self._get_session() as db:
            result = await db.execute(
                select(Ticket).order_by(Ticket.created_at.desc()).limit(limit)
            )
            return list(result.scalars().all())

    # ------ Analytics ------

    async def get_call_stats(self) -> dict:
        """Get basic call statistics for monitoring."""
        async with self._get_session() as db:
            from sqlalchemy import func
            result = await db.execute(select(func.count()).select_from(CallRecord))
            total_calls = result.scalar() or 0
            return {
                "total_calls": total_calls,
            }


# Singleton instance
db_service = DatabaseService()

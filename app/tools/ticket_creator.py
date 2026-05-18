"""
Ticket Creator Tool — Creates support tickets in PostgreSQL and sends email notification.
NO LLM needed — structured data is already available from slots.
"""

from typing import List, Dict, Any, Optional
from app.services.db_service import db_service
from app.models.agent_contracts import TicketCreate
from app.utils.logger import CallLogger

logger = CallLogger(call_id="ticket_tool")


class TicketCreator:
    """Creates support tickets and optionally sends email notifications."""

    async def create(
        self,
        call_id: str,
        slots: Dict[str, Any],
        diagnosis: str = "",
        steps: List[str] = None,
        sentiment: str = "neutral",
        priority: Optional[str] = None
    ) -> str:
        """
        Create a support ticket from the collected call data.
        
        Returns:
            ticket_number: The generated ticket ID (e.g., "KGE-20260409-A3F2B1")
        """
        try:
            # Use provided priority or determine automatically
            if not priority:
                priority = self._determine_priority(
                    slots.get("product_category", ""),
                    sentiment,
                )

            ticket_data = TicketCreate(
                call_id=call_id,
                customer_name=slots.get("customer_name"),
                phone_number=slots.get("phone_number", ""),
                contact_number=slots.get("contact_number"),
                product_category=slots.get("product_category"),
                product_model=slots.get("product_model"),
                serial_number=slots.get("serial_number"),
                city=slots.get("city"),
                error_code=slots.get("error_code"),
                issue_description=slots.get("issue_description"),
                diagnosis_attempted=diagnosis,
                troubleshooting_steps=steps or [],
                resolution_status="escalated",
                sentiment=sentiment,
                priority=priority,
            )

            # Save to real PostgreSQL
            ticket_number = await db_service.create_ticket(ticket_data)
            logger.info(f"Ticket created in DB: {ticket_number} (priority: {priority})")

            return ticket_number

        except Exception as e:
            logger.error(f"Ticket creation error: {e}")
            return f"KGE-ERR-{call_id[:6]}"

    def _determine_priority(self, product_category: str, sentiment: str) -> str:
        """Determine ticket priority based on product and sentiment."""
        # Oxygen Concentrator is always critical
        if product_category and "oxygen" in product_category.lower():
            return "critical"

        # Angry customer → high priority
        if sentiment == "angry":
            return "high"

        # Frustrated customer → normal-high
        if sentiment == "frustrated":
            return "normal"

        return "normal"


# Singleton
ticket_creator = TicketCreator()

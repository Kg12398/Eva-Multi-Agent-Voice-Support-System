"""
Warranty Lookup Tool — Simple DB/API function, NO LLM needed.
Checks warranty status by serial number.
"""

from typing import Optional
from app.utils.logger import CallLogger

logger = CallLogger(call_id="warranty_tool")

# In production, this would query a real database or API
# For now, using a mock lookup table
WARRANTY_DATABASE = {
    # Format: serial_number -> {status, expiry_date, product}
    "KGEP-2024-001": {"status": "active", "expiry": "2026-12-31", "product": "Inverter"},
    "KGEP-2024-002": {"status": "expired", "expiry": "2025-01-15", "product": "Solar Panel"},
    "KGEP-2023-003": {"status": "active", "expiry": "2025-06-30", "product": "3-Wheeler Battery"},
}


async def warranty_lookup(serial_number: str) -> str:
    """
    Look up warranty status by serial number.
    
    Args:
        serial_number: Product serial number (e.g., "KGEP-2024-001")
        
    Returns:
        Warranty status string: "active", "expired", or "unknown"
    """
    if not serial_number:
        return "unknown"

    try:
        serial_upper = serial_number.strip().upper()

        # Check mock database (replace with real DB query in production)
        if serial_upper in WARRANTY_DATABASE:
            record = WARRANTY_DATABASE[serial_upper]
            logger.info(f"Warranty found: {serial_upper} → {record['status']}")
            return record["status"]

        # TODO: In production, query PostgreSQL:
        # async with db_session() as db:
        #     result = await db.execute(
        #         select(WarrantyRecord).where(
        #             WarrantyRecord.serial_number == serial_upper
        #         )
        #     )
        #     record = result.scalar_one_or_none()
        #     return record.status if record else "unknown"

        logger.info(f"Warranty not found: {serial_upper}")
        return "unknown"

    except Exception as e:
        logger.error(f"Warranty lookup error: {e}")
        return "unknown"

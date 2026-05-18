"""
Pydantic models for call state, session, and slot management.
These models define the core data structures flowing through the system.
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


# ============================================
# FSM States
# ============================================

class CallState(str, Enum):
    """Finite State Machine states for the conversation flow."""
    GREETING = "GREETING"
    VERIFYING = "VERIFYING"
    COLLECTING = "COLLECTING"
    VALIDATING = "VALIDATING"
    CHECK_WARRANTY = "CHECK_WARRANTY"
    READY_FOR_DIAGNOSIS = "READY_FOR_DIAGNOSIS"
    DIAGNOSIS = "DIAGNOSIS"
    TROUBLESHOOTING = "TROUBLESHOOTING"
    DECISION = "DECISION"
    RESOLUTION = "RESOLUTION"
    ESCALATION = "ESCALATION"
    SAFETY_ESCALATION = "SAFETY_ESCALATION"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    CLOSURE = "CLOSURE"
    END = "END"


# ============================================
# Product & Issue Enums
# ============================================

class ProductCategory(str, Enum):
    """KG ElectroPower product categories."""
    SOLAR_PANEL = "Solar Panel"
    INVERTER = "Inverter"
    THREE_WHEELER_BATTERY = "3-Wheeler Battery"
    AIR_PURIFIER = "Air Purifier"
    OXYGEN_CONCENTRATOR = "Oxygen Concentrator"
    UNKNOWN = "Unknown"


class SentimentLevel(str, Enum):
    """Customer sentiment classification."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"


# ============================================
# Slot Model (Information to collect)
# ============================================

class Slots(BaseModel):
    """Structured information extracted from the conversation."""
    customer_name: Optional[str] = None
    contact_number: Optional[str] = None
    identifier_type: Optional[str] = None  # "order_id" or "serial_number"
    identifier_value: Optional[str] = None
    product_category: Optional[str] = None
    product_model: Optional[str] = None
    serial_number: Optional[str] = None
    issue_description: Optional[str] = None
    purchase_date: Optional[str] = None
    city: Optional[str] = None
    error_code: Optional[str] = None
    
    # Tracking fields
    already_asked: List[str] = Field(default_factory=list)
    question_just_asked: Optional[str] = None

    def get_missing_slots(self) -> List[str]:
        """Returns list of required slots that are still missing."""
        required = ["customer_name", "contact_number"]
        missing = []
        for slot in required:
            if getattr(self, slot) is None:
                missing.append(slot)
        return missing

    def all_required_filled(self) -> bool:
        """Check if all required slots are filled."""
        return len(self.get_missing_slots()) == 0

    def is_safety_critical(self) -> bool:
        """Check if the product is safety-critical (Oxygen Concentrator)."""
        if self.product_category:
            return self.product_category.lower() in [
                "oxygen concentrator",
                ProductCategory.OXYGEN_CONCENTRATOR.value.lower(),
            ]
        return False


# ============================================
# Conversation Message
# ============================================

class ConversationMessage(BaseModel):
    """A single message in the conversation history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# Call Session (Full session state stored in Redis)
# ============================================

class CallSession(BaseModel):
    """Complete state for a single call, persisted in Redis."""
    call_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    phone_number: str = ""
    state: CallState = CallState.GREETING
    slots: Slots = Field(default_factory=Slots)
    customer_verified: bool = False
    abusive_warning_sent: bool = False
    warranty_status: Optional[str] = None
    diagnosis_result: Optional[str] = None
    diagnosis_steps: List[str] = Field(default_factory=list)
    sentiment: SentimentLevel = SentimentLevel.NEUTRAL
    turn_count: int = 0
    retry_count: int = 0  # troubleshooting retry attempts
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    ticket_id: Optional[str] = None
    resolution_status: Optional[str] = None  # "resolved" | "escalated" | "abandoned"
    should_escalate: bool = False
    rag_context: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

    def add_message(self, role: str, content: str):
        """Add a message to conversation history and increment turn count."""
        self.conversation_history.append(
            ConversationMessage(role=role, content=content)
        )
        if role == "user":
            self.turn_count += 1

    def is_max_turns_reached(self) -> bool:
        """Check if conversation has exceeded max turn limit."""
        return self.turn_count >= 20

    def get_history_for_llm(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation history formatted for LLM input."""
        recent = self.conversation_history[-max_messages:]
        return [{"role": msg.role, "content": msg.content} for msg in recent]

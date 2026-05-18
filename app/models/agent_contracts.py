"""
Pydantic models for standardized agent request/response contracts.
All agents communicate through these schemas via the Orchestrator.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ============================================
# Agent Request (Orchestrator → Agent)
# ============================================

class AgentRequest(BaseModel):
    """Standardized request sent from Orchestrator to any agent."""
    call_id: str
    user_input: str
    state: str  # Current FSM state
    slots: Dict[str, Any]  # Current slot values
    conversation_history: List[Dict[str, str]]  # Recent messages
    turn_number: int
    sentiment: str = "neutral"
    ticket_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================
# Agent Response (Agent → Orchestrator)
# ============================================

class AgentResponse(BaseModel):
    """Standardized response from any agent back to the Orchestrator."""
    status: str = "success"  # "success" | "error" | "needs_info"
    response_text: str = ""  # Text to speak to the user
    extracted_slots: Dict[str, Any] = Field(default_factory=dict)  # Newly extracted info
    sentiment: str = "neutral"
    confidence: float = 0.0  # 0.0 to 1.0
    next_action: str = ""  # Suggested next FSM state
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================
# LLM Structured Output (Single LLM Call)
# ============================================

class ConversationLLMOutput(BaseModel):
    """
    Structured output from the single Gemini LLM call.
    Handles slot extraction + response generation + sentiment in ONE call.
    """
    extracted_slots: Dict[str, Optional[Any]] = Field(default_factory=dict)
    customer_verified: bool = False
    sentiment: str = "neutral"
    response_text: str = ""
    next_state: str = "COLLECTING"
    needs_rag_lookup: bool = False
    needs_escalation: bool = False
    needs_db_lookup: bool = False
    confidence: float = 0.8
    unclear_input: bool = False
    question_just_asked: Optional[str] = None


# ============================================
# RAG Agent Output
# ============================================

class RAGResponse(BaseModel):
    """Response from the RAG/Diagnosis agent."""
    diagnosis: str = ""
    product_specific_warning: Optional[str] = None
    troubleshooting_steps: List[str] = Field(default_factory=list)
    mid_check_question: Optional[str] = None
    follow_up_question: Optional[str] = None
    confidence: float = 0.0
    source_documents: List[str] = Field(default_factory=list)
    resolved: bool = False
    requires_field_visit: bool = False
    escalation_reason: Optional[str] = None


# ============================================
# Decision Agent Output
# ============================================

class DecisionResponse(BaseModel):
    """Response from the Decision agent."""
    action: str = "continue"  # "continue" | "resolve" | "partial_resolve" | "escalate"
    ticket_priority: Optional[str] = None
    reason: str = ""
    retry_angle: Optional[str] = None
    sla: Optional[str] = None
    confidence: float = 0.0


# ============================================
# Ticket Model
# ============================================

class TicketCreate(BaseModel):
    """Data for creating a support ticket."""
    call_id: str
    customer_name: Optional[str] = None
    phone_number: str = ""
    contact_number: Optional[str] = None
    product_category: Optional[str] = None
    product_model: Optional[str] = None
    serial_number: Optional[str] = None
    city: Optional[str] = None
    error_code: Optional[str] = None
    issue_description: Optional[str] = None
    diagnosis_attempted: str = ""
    troubleshooting_steps: List[str] = Field(default_factory=list)
    resolution_status: str = "escalated"
    sentiment: str = "neutral"
    call_summary: str = ""
    priority: str = "normal"  # "low" | "normal" | "high" | "critical"

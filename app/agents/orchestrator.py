"""
LangGraph Orchestrator — The Central Brain of the Voice Agent System.
Implements a slot-driven Finite State Machine that controls the entire conversation flow.
All agents communicate through this orchestrator — they NEVER talk to each other directly.
"""

from datetime import datetime
from typing import TypedDict, Annotated, Optional, List, Dict, Any, Literal
from langgraph.graph import StateGraph, END
from app.agents.conversation_agent import ConversationAgent
from app.agents.rag_agent import RAGAgent
from app.agents.decision_agent import DecisionAgent
from app.tools.warranty_lookup import warranty_lookup
from app.tools.ticket_creator import TicketCreator
from app.models.call_state import CallSession, CallState, Slots, SentimentLevel
from app.models.agent_contracts import AgentRequest
from app.services.redis_service import redis_service
from app.utils.constants import (
    GREETING_MESSAGE,
    CLOSURE_MESSAGE_RESOLVED,
    CLOSURE_MESSAGE_ESCALATED,
    SAFETY_ESCALATION_MESSAGE,
    MAX_TURNS_MESSAGE,
    CLOSURE_MESSAGE_ESCALATED_ANGRY,
    OUT_OF_SCOPE_MESSAGE
)
from app.utils.logger import CallLogger


# ============================================
# LangGraph State Definition
# ============================================

class ConversationState(TypedDict):
    """State that flows through the LangGraph state machine."""
    call_id: str
    user_input: str
    current_state: str  # maps to CallState
    slots: Dict[str, Any]
    sentiment: str
    turn_count: int
    retry_count: int
    conversation_history: List[Dict[str, str]]
    warranty_status: Optional[str]
    diagnosis_result: Optional[str]
    diagnosis_steps: List[str]
    rag_context: Optional[str]
    response: str
    should_escalate: bool
    ticket_id: Optional[str]
    is_complete: bool
    customer_verified: bool
    abusive_warning_sent: bool
    already_asked: List[str]
    question_just_asked: Optional[str]


# ============================================
# Orchestrator Class
# ============================================

class Orchestrator:
    """
    The central brain — implements a LangGraph state machine
    that controls the entire conversation flow.
    """

    def __init__(self, vector_store=None):
        self.conversation_agent = ConversationAgent()
        self.rag_agent = RAGAgent(vector_store=vector_store)
        self.decision_agent = DecisionAgent()
        self.ticket_creator = TicketCreator()
        self.graph = self._build_graph()
        self.logger = CallLogger(call_id="orchestrator")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine exactly following prompt Phases."""

        graph = StateGraph(ConversationState)

        # --- Add Nodes ---
        graph.add_node("router", self._router_node)
        graph.add_node("greeting", self._greeting_node)
        graph.add_node("verifying", self._verifying_node)
        graph.add_node("collecting", self._collecting_node)
        graph.add_node("ready_for_diagnosis", self._ready_for_diagnosis_node)
        graph.add_node("troubleshooting", self._troubleshooting_node)
        graph.add_node("decision", self._decision_node)
        graph.add_node("out_of_scope", self._out_of_scope_node)
        graph.add_node("escalation", self._escalation_node)
        graph.add_node("safety_escalation", self._safety_escalation_node)
        graph.add_node("closure", self._closure_node)

        # --- Add Edges (Strict Flow) ---
        graph.set_entry_point("router")

        # Dynamic entry routing
        graph.add_conditional_edges(
            "router",
            self._route_by_state,
            {
                "greeting": "greeting",
                "verifying": "verifying",
                "collecting": "collecting",
                "ready_for_diagnosis": "ready_for_diagnosis",
                "troubleshooting": "troubleshooting",
                "decision": "decision",
                "out_of_scope": "out_of_scope",
                "escalation": "escalation",
                "safety_escalation": "safety_escalation",
                "closure": "closure"
            }
        )

        graph.add_edge("greeting", "verifying")

        # Routing from VERIFYING
        graph.add_conditional_edges(
            "verifying",
            self._route_after_conversation,
            {
                "verifying": END,
                "collecting": END,
                "ready_for_diagnosis": "ready_for_diagnosis",
                "out_of_scope": "out_of_scope",
                "escalation": "escalation",
                "safety_escalation": "safety_escalation"
            }
        )

        # Routing from COLLECTING
        graph.add_conditional_edges(
            "collecting",
            self._route_after_conversation,
            {
                "collecting": END,
                "ready_for_diagnosis": "ready_for_diagnosis",
                "out_of_scope": "out_of_scope",
                "escalation": "escalation",
                "safety_escalation": "safety_escalation"
            }
        )

        # Hand off to Diagnosis
        graph.add_edge("ready_for_diagnosis", "troubleshooting")
        graph.add_edge("troubleshooting", "decision")

        # Decision Routing
        graph.add_conditional_edges(
            "decision",
            self._route_after_decision,
            {
                "troubleshooting": END,
                "escalation": "escalation",
                "closure": "closure"
            }
        )

        # Terminal Nodes
        graph.add_edge("out_of_scope", END)
        graph.add_edge("safety_escalation", END)
        graph.add_edge("escalation", "closure")
        graph.add_edge("closure", END)

        return graph.compile()

    # ============================================
    # Entry Point Router Logic
    # ============================================

    async def _router_node(self, state: ConversationState) -> ConversationState:
        """Entry point that reads current state and directs to the appropriate node."""
        return state

    def _route_by_state(self, state: ConversationState) -> str:
        """Maps current state string to graph node name."""
        cur = state.get("current_state", "GREETING")
        
        mapping = {
            "GREETING": "greeting",
            "VERIFYING": "verifying",
            "COLLECTING": "collecting",
            "READY_FOR_DIAGNOSIS": "ready_for_diagnosis",
            "DIAGNOSIS": "troubleshooting",
            "TROUBLESHOOTING": "troubleshooting",
            "DECISION": "decision",
            "OUT_OF_SCOPE": "out_of_scope",
            "ESCALATING": "escalation",
            "ESCALATION": "escalation",
            "SAFETY_ESCALATION": "safety_escalation",
            "RESOLUTION": "closure",
            "CLOSURE": "closure"
        }
        
        node = mapping.get(cur, "verifying")
        return node

    # ============================================
    # Public API
    # ============================================

    async def process_turn(self, call_id: str, user_input: str) -> str:
        """
        Process a single user turn and return the response text.
        """
        # Load session from Redis
        session = await redis_service.get_session(call_id)
        if not session:
            session = CallSession(call_id=call_id)

        # Record user message
        session.add_message("user", user_input)

        # Build LangGraph state from session
        state: ConversationState = {
            "call_id": call_id,
            "user_input": user_input,
            "current_state": session.state.value,
            "slots": session.slots.model_dump(),
            "sentiment": str(session.sentiment.value if hasattr(session.sentiment, 'value') else session.sentiment),
            "turn_count": session.turn_count,
            "retry_count": session.retry_count,
            "conversation_history": session.get_history_for_llm(),
            "warranty_status": session.warranty_status,
            "diagnosis_result": session.diagnosis_result,
            "diagnosis_steps": session.diagnosis_steps,
            "rag_context": session.rag_context,
            "response": "",
            "should_escalate": session.should_escalate,
            "ticket_id": session.ticket_id,
            "is_complete": False,
            "customer_verified": session.customer_verified,
            "abusive_warning_sent": session.abusive_warning_sent,
            "already_asked": session.slots.already_asked,
            "question_just_asked": session.slots.question_just_asked
        }

        # Run the graph
        result = await self.graph.ainvoke(state)

        # Update session from result
        response_text = result.get("response", "")
        self._update_session_from_state(session, result)
        session.add_message("assistant", response_text)

        # Save session back to Redis
        await redis_service.save_session(session)

        self.logger.info(
            f"Turn {session.turn_count} | State: {session.state.value} | "
            f"Sentiment: {session.sentiment}"
        )

        return response_text

    async def start_call(self, call_id: str, phone_number: str = "") -> str:
        """Initialize a new call and return the greeting."""
        session = CallSession(call_id=call_id, phone_number=phone_number)
        session.state = CallState.VERIFYING  # Phase 1
        session.add_message("assistant", GREETING_MESSAGE)
        await redis_service.save_session(session)
        self.logger.info(f"New call started: {call_id}")
        return GREETING_MESSAGE

    async def end_call(self, call_id: str):
        """Clean up after a call ends and save to permanent DB."""
        from app.services.db_service import db_service
        session = await redis_service.get_session(call_id)
        if session:
            session.state = CallState.END
            # SAVE to permanent PostgreSQL database
            await db_service.save_call_record(session)
            # Now safe to delete from temporary Redis
            await redis_service.delete_session(call_id)
            
        self.logger.info(f"Call ended and saved to DB: {call_id}")
        return session

    # ============================================
    # Graph Nodes
    # ============================================

    # ============================================
    # Graph Nodes (Phases)
    # ============================================

    async def _greeting_node(self, state: ConversationState) -> ConversationState:
        """Initial greeting."""
        state["response"] = GREETING_MESSAGE
        state["current_state"] = CallState.VERIFYING.value
        return state

    async def _verifying_node(self, state: ConversationState) -> ConversationState:
        """Phase 1: Customer Identity Check."""
        return await self._conversation_step(state, phase="PHASE 1: VERIFYING")

    async def _collecting_node(self, state: ConversationState) -> ConversationState:
        """Phase 2: Issue Detail Collection."""
        return await self._conversation_step(state, phase="PHASE 2: COLLECTING")

    async def _conversation_step(self, state: ConversationState, phase: str) -> ConversationState:
        """Helper to run a conversation turn using ConversationAgent."""
        # Preparation
        metadata = {
            "current_phase": phase,
            "already_asked": state["already_asked"],
            "attempted_steps": state["diagnosis_steps"],
            "customer_verified": state["customer_verified"],
            "abusive_warning_sent": state["abusive_warning_sent"]
        }

        request = AgentRequest(
            call_id=state["call_id"],
            user_input=state["user_input"],
            state=state["current_state"],
            slots=state["slots"],
            conversation_history=state["conversation_history"],
            turn_number=state["turn_count"],
            sentiment=state["sentiment"],
            ticket_id=state["ticket_id"],
            metadata=metadata
        )

        response = await self.conversation_agent.process(request)

        # Update slots and session flags
        if response.extracted_slots:
            for key, value in response.extracted_slots.items():
                if value is not None and value != "null":
                    state["slots"][key] = value

        # Update metadata flags
        if "customer_verified" in response.metadata:
            state["customer_verified"] = response.metadata["customer_verified"]
        if "question_just_asked" in response.metadata:
            state["question_just_asked"] = response.metadata["question_just_asked"]
            if state["question_just_asked"] and state["question_just_asked"] not in state["already_asked"]:
                state["already_asked"].append(state["question_just_asked"])

        state["sentiment"] = response.sentiment
        state["response"] = response.response_text
        state["current_state"] = response.next_action # VERIFYING|COLLECTING|...
        
        return state

    async def _ready_for_diagnosis_node(self, state: ConversationState) -> ConversationState:
        """Phase 3: Hand off to RAG Agent."""
        state["current_state"] = CallState.TROUBLESHOOTING.value
        return state

    async def _troubleshooting_node(self, state: ConversationState) -> ConversationState:
        """Phase 4: RAG-powered diagnosis."""
        rag_response = await self.rag_agent.diagnose(
            product_category=state["slots"].get("product_category", "Unknown"),
            product_model=state["slots"].get("product_model"),
            issue_description=state["slots"].get("issue_description", ""),
            customer_name=state["slots"].get("customer_name", "Customer"),
            error_code=state["slots"].get("error_code"),
            city=state["slots"].get("city"),
            customer_verified=state["customer_verified"],
            warranty_status=state["warranty_status"] or "unknown",
            rag_context=state["rag_context"] or ""
        )

        state["diagnosis_result"] = rag_response.diagnosis
        state["diagnosis_steps"] = rag_response.troubleshooting_steps

        # Build response with troubleshooting steps (using prompt guidance)
        steps_text = ""
        if rag_response.troubleshooting_steps:
             steps_text = " ".join(rag_response.troubleshooting_steps[:2])
             if rag_response.product_specific_warning:
                 state["response"] = f"{rag_response.product_specific_warning} {steps_text} {rag_response.mid_check_question or ''}"
             else:
                 state["response"] = f"Based on what you've described, {rag_response.diagnosis}. {steps_text} {rag_response.mid_check_question or ''}"
        else:
            state["response"] = f"Based on what you've described, {rag_response.diagnosis}. Let me check with our technical team."

        state["retry_count"] = state.get("retry_count", 0) + 1
        return state

    async def _decision_node(self, state: ConversationState) -> ConversationState:
        """Phase 4.5: Decide next action."""
        slots = Slots(**state["slots"])

        decision = await self.decision_agent.decide(
            issue_description=state["slots"].get("issue_description", ""),
            product_category=state["slots"].get("product_category", "Unknown"),
            confidence=0.7,
            retry_count=state.get("retry_count", 0),
            sentiment=state["sentiment"],
            last_message=state["user_input"],
            is_safety_critical=slots.is_safety_critical(),
            requires_field_visit=state.get("is_complete", False), # simplified for now
            is_business_hours=True # default
        )

        if decision.action == "escalate":
            state["should_escalate"] = True
            state["current_state"] = CallState.ESCALATION.value
            state["metadata"] = state.get("metadata", {})
            state["metadata"]["sla"] = decision.sla
            state["metadata"]["ticket_priority"] = decision.ticket_priority
        elif decision.action == "resolve":
            state["should_escalate"] = False
            state["current_state"] = CallState.RESOLUTION.value
        elif decision.action == "continue":
            state["current_state"] = CallState.TROUBLESHOOTING.value

        return state

    async def _out_of_scope_node(self, state: ConversationState) -> ConversationState:
        """Terminal node for sales/pricing queries."""
        from app.utils.constants import OUT_OF_SCOPE_MESSAGE
        state["response"] = OUT_OF_SCOPE_MESSAGE
        state["is_complete"] = True
        state["current_state"] = CallState.END.value
        return state

    async def _escalation_node(self, state: ConversationState) -> ConversationState:
        """Create a support ticket and prepare escalation message."""
        sla = state.get("metadata", {}).get("sla", "24 hours")
        priority = state.get("metadata", {}).get("ticket_priority", "normal")
        
        ticket_id = await self.ticket_creator.create(
            call_id=state["call_id"],
            slots=state["slots"],
            diagnosis=state.get("diagnosis_result", ""),
            steps=state.get("diagnosis_steps", []),
            sentiment=state["sentiment"],
            priority=priority
        )
        state["ticket_id"] = ticket_id
        
        # Use localized closure messages
        if state["sentiment"] == "angry":
            from app.utils.constants import CLOSURE_MESSAGE_ESCALATED_ANGRY
            state["response"] = CLOSURE_MESSAGE_ESCALATED_ANGRY.format(
                customer_name=state["slots"].get("customer_name", "Customer"),
                ticket_id=ticket_id,
                sla=sla
            )
        else:
            from app.utils.constants import CLOSURE_MESSAGE_ESCALATED
            state["response"] = CLOSURE_MESSAGE_ESCALATED.format(
                customer_name=state["slots"].get("customer_name", "Customer"),
                ticket_id=ticket_id,
                sla=sla
            )

        state["current_state"] = CallState.END.value
        state["is_complete"] = True
        return state

    async def _safety_escalation_node(self, state: ConversationState) -> ConversationState:
        """Highest priority escalation for medical devices."""
        from app.utils.constants import SAFETY_ESCALATION_MESSAGE
        ticket_id = await self.ticket_creator.create(
            call_id=state["call_id"],
            slots=state["slots"],
            diagnosis="Safety-critical medical device issue",
            steps=[],
            sentiment=state["sentiment"],
            priority="critical"
        )
        state["ticket_id"] = ticket_id
        state["response"] = SAFETY_ESCALATION_MESSAGE.format(ticket_id=ticket_id)
        state["current_state"] = CallState.END.value
        state["is_complete"] = True
        return state

    async def _closure_node(self, state: ConversationState) -> ConversationState:
        """Final closure message."""
        if not state.get("should_escalate") and not state.get("ticket_id"):
            from app.utils.constants import CLOSURE_MESSAGE_RESOLVED
            state["response"] = CLOSURE_MESSAGE_RESOLVED.format(
                customer_name=state["slots"].get("customer_name", "Customer")
            )

        state["current_state"] = CallState.END.value
        state["is_complete"] = True
        return state

    async def end_call(self, call_id: str):
        """Clean up after a call ends and save to permanent DB."""
        from app.services.db_service import db_service
        session = await redis_service.get_session(call_id)
        if session:
            session.state = CallState.END
            await db_service.save_call_record(session)
            await redis_service.delete_session(call_id)
        return session

    # ============================================
    # Routing Functions
    # ============================================

    def _route_after_conversation(self, state: ConversationState) -> str:
        """Routes from Verifying or Collecting phases."""
        next_val = state["current_state"]
        if next_val == "OUT_OF_SCOPE": return "out_of_scope"
        if next_val == "SAFETY_ESCALATION": return "safety_escalation"
        if next_val == "ESCALATING": return "escalation"
        if next_val == "READY_FOR_DIAGNOSIS": return "ready_for_diagnosis"
        if next_val == "VERIFYING": return "verifying"
        if next_val == "COLLECTING": return "collecting"
        return "collecting"

    def _route_after_decision(self, state: ConversationState) -> str:
        """Route based on decision agent's output."""
        if state["current_state"] == CallState.RESOLUTION.value:
            return "closure"
        if state["current_state"] == CallState.ESCALATION.value:
            return "escalation"
        return "troubleshooting"

    # ============================================
    # Helpers
    # ============================================

    def _state_to_node(self, state: CallState) -> str:
        """Map CallState enum to initial graph node."""
        mapping = {
            CallState.GREETING: "greeting",
            CallState.VERIFYING: "verifying",
            CallState.COLLECTING: "collecting",
            CallState.TROUBLESHOOTING: "troubleshooting",
            CallState.ESCALATION: "escalation",
            CallState.CLOSURE: "closure",
        }
        return mapping.get(state, "verifying")

    def _update_session_from_state(self, session: CallSession, state: ConversationState):
        """Update the CallSession from LangGraph state after processing."""
        from datetime import datetime
        for key, value in state["slots"].items():
            if value is not None and hasattr(session.slots, key):
                setattr(session.slots, key, value)
        
        session.slots.already_asked = state.get("already_asked", [])
        session.slots.question_just_asked = state.get("question_just_asked")

        try:
            session.state = CallState(state["current_state"])
        except (ValueError, KeyError):
            session.state = CallState.COLLECTING

        try:
            session.sentiment = SentimentLevel(state.get("sentiment", "neutral"))
        except ValueError:
            session.sentiment = SentimentLevel.NEUTRAL
        session.customer_verified = state.get("customer_verified", False)
        session.abusive_warning_sent = state.get("abusive_warning_sent", False)
        session.warranty_status = state.get("warranty_status")
        session.diagnosis_result = state.get("diagnosis_result")
        session.diagnosis_steps = state.get("diagnosis_steps", [])
        session.should_escalate = state.get("should_escalate", False)
        session.ticket_id = state.get("ticket_id")
        session.retry_count = state.get("retry_count", 0)

        if state.get("is_complete"):
            session.resolution_status = "escalated" if session.should_escalate or session.state == CallState.SAFETY_ESCALATION else "resolved"
            session.ended_at = datetime.utcnow()

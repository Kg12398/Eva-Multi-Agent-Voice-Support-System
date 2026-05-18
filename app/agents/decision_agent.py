"""
Decision Agent — Determines whether to resolve, continue troubleshooting, or escalate.
"""

import json
from langchain_groq import ChatGroq
from app.models.agent_contracts import DecisionResponse
from app.utils.constants import DECISION_AGENT_PROMPT
from app.config import settings
from app.utils.logger import CallLogger


class DecisionAgent:
    """
    Makes the critical decision: resolved, continue, or escalate.
    Uses Groq (Llama 3.3 70B) with strict rules about safety-critical products.
    """

    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=settings.GROQ_API_KEY,
            temperature=0.1,
            max_tokens=200,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        self.logger = CallLogger(call_id="decision_agent")

    async def decide(
        self,
        issue_description: str,
        product_category: str,
        confidence: float,
        retry_count: int,
        sentiment: str,
        last_message: str,
        is_safety_critical: bool,
        requires_field_visit: bool = False,
        is_business_hours: bool = True
    ) -> DecisionResponse:
        """
        Evaluate the current state and decide next action.
        """
        # Hard rules (bypass LLM for deterministic decisions)
        if is_safety_critical:
            return DecisionResponse(
                action="escalate",
                reason="Safety-critical product (Oxygen Concentrator) — auto-escalating",
                ticket_priority="critical",
                sla="1 hour",
                confidence=1.0,
            )

        if retry_count >= 3:
            return DecisionResponse(
                action="escalate",
                reason=f"Maximum troubleshooting attempts reached ({retry_count})",
                ticket_priority="high",
                sla="24 hours",
                confidence=0.95,
            )

        # Check if user explicitly asks for human help
        human_keywords = ["human", "agent", "person", "supervisor", "manager", "real person", "talk to someone", "insaan", "insan"]
        if any(kw in last_message.lower() for kw in human_keywords):
            return DecisionResponse(
                action="escalate",
                reason="Customer explicitly requested human assistance",
                ticket_priority="normal",
                sla="24 hours",
                confidence=1.0,
            )

        # For nuanced decisions, use LLM
        try:
            prompt = DECISION_AGENT_PROMPT.format(
                issue_description=issue_description,
                product_category=product_category,
                confidence=confidence,
                retry_count=retry_count,
                sentiment=sentiment,
                last_message=last_message,
                is_safety_critical="True" if is_safety_critical else "False",
                requires_field_visit="True" if requires_field_visit else "False",
                is_business_hours="True" if is_business_hours else "False"
            )

            messages = [
                ("user", prompt),
                ("user", "IMPORTANT: Respond ONLY with the JSON object. No conversational filler.")
            ]

            response = await self.llm.ainvoke(messages)
            return self._parse_output(response.content)

        except Exception as e:
            self.logger.error(f"Decision agent error: {e}")
            # Safe default: escalate on error
            return DecisionResponse(
                action="escalate",
                reason="Decision agent error — escalating for safety",
                confidence=0.5,
            )

    def _parse_output(self, raw: str) -> DecisionResponse:
        """Parse decision output with robust extraction."""
        try:
            import re
            match = re.search(r"(\{.*\})", raw, re.DOTALL)
            if match:
                clean = match.group(1)
            else:
                clean = raw.strip()

            if clean.startswith("```"):
                lines = clean.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean = "\n".join(lines).strip()
            
            if clean.startswith("json"):
                clean = clean[4:].strip()

            data = json.loads(clean)
            return DecisionResponse(**data)
        except Exception:
            # Default to escalation if parsing fails
            return DecisionResponse(
                action="escalate",
                reason="Unable to parse decision — escalating for safety",
                confidence=0.5,
            )

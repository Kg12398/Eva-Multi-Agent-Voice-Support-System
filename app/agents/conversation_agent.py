"""
Conversation Agent — The primary LLM-powered agent.
Handles slot extraction + response generation + sentiment detection in a SINGLE Groq call.
"""

import json
import asyncio
from typing import Dict, Any, Optional
from langchain_groq import ChatGroq
from app.models.agent_contracts import AgentRequest, AgentResponse, ConversationLLMOutput
from app.utils.constants import CONVERSATION_AGENT_PROMPT, GENERAL_ERROR_MESSAGE
from app.config import settings
from app.utils.logger import CallLogger

# Groq rate limit error keyword
_RATE_LIMIT_KEYWORDS = ["rate_limit_exceeded", "rate limit", "429", "tokens per day"]


class ConversationAgent:
    """
    Core agent that processes every user turn.
    Uses Groq (Llama 3.3 70B) for ultra-fast inference (~100ms first token).
    Single call to simultaneously:
    - Extract slot information from user's speech
    - Detect sentiment
    - Generate the spoken response
    """

    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=settings.GROQ_API_KEY,
            temperature=0.1, # Lower temperature for better JSON compliance
            max_tokens=500,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        self.logger = CallLogger(call_id="conversation_agent")

    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        Process a user turn and return the agent response.
        
        Args:
            request: Standardized agent request with user input, state, and context
            
        Returns:
            AgentResponse with extracted slots, sentiment, and spoken response
        """
        try:
            # Build the prompt with current slot state
            missing_slots = [k for k, v in request.slots.items() if v is None]
            filled_slots = {k: v for k, v in request.slots.items() if v is not None}

            metadata_in = request.metadata or {}
            system_prompt = CONVERSATION_AGENT_PROMPT.format(
                current_phase=metadata_in.get("current_phase", "INITIAL"),
                current_state=request.state,
                missing_slots=", ".join(missing_slots) if missing_slots else "None",
                filled_slots=json.dumps(filled_slots, indent=2),
                already_asked=json.dumps(metadata_in.get("already_asked", [])),
                attempted_steps=json.dumps(metadata_in.get("attempted_steps", [])),
                retry_count=request.turn_number,
                customer_verified="True" if metadata_in.get("customer_verified") else "False",
                abusive_warning_sent="True" if metadata_in.get("abusive_warning_sent") else "False",
                ticket_id=request.ticket_id or "Pending"
            )

            # Build conversation messages
            messages = [("system", system_prompt)]

            # Add relevant conversation history (last 6 messages for context)
            for msg in request.conversation_history[-6:]:
                messages.append((msg["role"], msg["content"]))

            # Add current user input
            messages.append(("user", request.user_input))
            
            # MANDATORY JSON REMINDER for Llama 3
            messages.append(("user", "IMPORTANT: Respond ONLY with the JSON object defined in the system prompt. No conversational filler before or after the JSON."))

            # Single LLM call — with rate-limit retry
            raw_output = await self._invoke_with_retry(messages)

            # Parse structured JSON output
            llm_output = self._parse_output(raw_output)

            return AgentResponse(
                status="success",
                response_text=llm_output.response_text,
                extracted_slots=llm_output.extracted_slots,
                sentiment=llm_output.sentiment,
                confidence=llm_output.confidence,
                next_action=llm_output.next_state,
                metadata={
                    "needs_rag_lookup": llm_output.needs_rag_lookup,
                    "customer_verified": llm_output.customer_verified,
                    "unclear_input": llm_output.unclear_input,
                    "question_just_asked": llm_output.question_just_asked,
                    "needs_escalation": llm_output.needs_escalation,
                    "raw_output": raw_output,
                },
            )

        except Exception as e:
            err_str = str(e).lower()
            if any(k in err_str for k in _RATE_LIMIT_KEYWORDS):
                self.logger.error(f"Groq rate limit hit (no more retries): {e}")
                # Keep the conversation alive — preserve state by NOT changing next_action
                return AgentResponse(
                    status="error",
                    response_text="I'm sorry, I'm experiencing a short delay. Could you please repeat your last message?",
                    next_action=request.state,  # stay in the same FSM state
                    confidence=0.0,
                )
            self.logger.error(f"Conversation agent error: {e}")
            return AgentResponse(
                status="error",
                response_text=GENERAL_ERROR_MESSAGE,
                next_action=request.state,
                confidence=0.0,
            )

    async def _invoke_with_retry(self, messages: list, max_retries: int = 2) -> str:
        """Invoke the LLM with exponential backoff on rate-limit errors."""
        for attempt in range(max_retries + 1):
            try:
                response = await self.llm.ainvoke(messages)
                return response.content
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = any(k in err_str for k in _RATE_LIMIT_KEYWORDS)
                if is_rate_limit and attempt < max_retries:
                    wait = 2 ** attempt  # 1s, 2s
                    self.logger.warning(f"Rate limit hit, retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait)
                else:
                    raise
        raise RuntimeError("Should not reach here")

    def _parse_output(self, raw: str) -> ConversationLLMOutput:
        """Parse the LLM response, which should be JSON."""
        try:
            import re
            # Find the first { and last } to extract JSON from potential conversational filler
            match = re.search(r"(\{.*\})", raw, re.DOTALL)
            if match:
                clean = match.group(1)
            else:
                clean = raw.strip()

            # Handle common markdown block issues
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
            return ConversationLLMOutput(**data)
        except (json.JSONDecodeError, Exception) as e:
            self.logger.warning(f"Failed to parse LLM JSON output: {e}. Raw: {raw[:100]}...")
            # Fallback: treat the entire response as plain text
            return ConversationLLMOutput(
                response_text=raw,
                confidence=0.5,
                next_state="COLLECTING" # Default move forward if parsing fails
            )

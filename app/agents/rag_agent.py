"""
RAG Agent — Knowledge Base Lookup & Diagnosis.
Queries ChromaDB vector store with the customer's issue and generates troubleshooting steps.
"""

import json
from typing import Optional, List
from langchain_groq import ChatGroq
from app.models.agent_contracts import AgentRequest, RAGResponse
from app.utils.constants import RAG_AGENT_PROMPT
from app.config import settings
from app.utils.logger import CallLogger


class RAGAgent:
    """
    Queries the knowledge base (ChromaDB) for relevant troubleshooting
    information and generates diagnosis + steps using Groq (Llama 3.3 70B).
    """

    def __init__(self, vector_store=None):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=settings.GROQ_API_KEY,
            temperature=0.1,
            max_tokens=600,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        self.vector_store = vector_store  # ChromaDB instance, injected
        self.logger = CallLogger(call_id="rag_agent")

    async def diagnose(
        self,
        product_category: str,
        product_model: Optional[str],
        issue_description: str,
        customer_name: str = "Customer",
        error_code: Optional[str] = None,
        city: Optional[str] = None,
        customer_verified: bool = False,
        warranty_status: str = "unknown",
        rag_context: str = ""
    ) -> RAGResponse:
        """
        Look up the knowledge base and generate a diagnosis.
        """
        try:
            # Step 1: Retrieve context if not provided
            if not rag_context:
                rag_context = await self._retrieve_context(
                    product_category, issue_description
                )

            # Step 2: Generate diagnosis using retrieved context
            prompt = RAG_AGENT_PROMPT.format(
                product_category=product_category,
                product_model=product_model or "Not specified",
                issue_description=issue_description,
                customer_name=customer_name,
                error_code=error_code or "None",
                city=city or "Unknown",
                customer_verified="True" if customer_verified else "False",
                warranty_status=warranty_status,
                rag_context=rag_context or "No specific documentation found. Use general core knowledge of this product line.",
            )

            messages = [
                ("user", prompt),
                ("user", "IMPORTANT: Respond ONLY with the JSON object defined in the system prompt. No conversational filler.")
            ]

            response = await self.llm.ainvoke(messages)
            raw_output = response.content

            # Parse response
            return self._parse_output(raw_output)

        except Exception as e:
            self.logger.error(f"RAG agent error: {e}")
            return RAGResponse(
                diagnosis="Unable to perform diagnosis at this time.",
                troubleshooting_steps=["Please try restarting your device."],
                confidence=0.2,
            )

    async def _retrieve_context(
        self, product_category: str, issue: str
    ) -> Optional[str]:
        """Retrieve relevant documents from ChromaDB vector store."""
        if not self.vector_store:
            self.logger.warning("No vector store configured, using LLM knowledge only")
            return None

        try:
            # Build the search query
            query = f"{product_category} {issue}"

            # Search ChromaDB
            results = self.vector_store.similarity_search(query, k=3)

            if results:
                context = "\n\n---\n\n".join(
                    [doc.page_content for doc in results]
                )
                self.logger.info(f"Retrieved {len(results)} relevant documents")
                return context

            return None

        except Exception as e:
            self.logger.error(f"ChromaDB retrieval error: {e}")
            return None

    def _parse_output(self, raw: str) -> RAGResponse:
        """Parse the LLM diagnosis response."""
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
            return RAGResponse(**data)
        except (json.JSONDecodeError, Exception) as e:
            self.logger.warning(f"Failed to parse RAG output: {e}. Raw: {raw[:100]}...")
            return RAGResponse(
                diagnosis=raw if len(raw) < 200 else "Diagnosis could not be parsed.",
                troubleshooting_steps=["Please contact our support team."],
                confidence=0.3,
            )

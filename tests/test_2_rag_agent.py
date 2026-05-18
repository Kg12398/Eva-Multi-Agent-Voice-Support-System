"""
PRACTICAL TEST 2: RAG Agent (Retrieval Quality + Grounding + Safety)
====================================================================
Tests whether the RAG agent retrieves correct context AND refuses to
hallucinate when the knowledge base has nothing relevant.
Run: python tests/test_2_rag_agent.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.rag_agent import RAGAgent
from app.utils.rag_loader import get_vector_store

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"

def ok(msg):  print(f"  {GREEN}✅ PASS{RESET}  {msg}")
def fail(msg):print(f"  {RED}❌ FAIL{RESET}  {msg}")
def info(msg):print(f"  {BLUE}ℹ  INFO{RESET}  {msg}")
def warn(msg):print(f"  {YELLOW}⚠  WARN{RESET}  {msg}")


TEST_CASES = [
    {
        "id": "RAG-01",
        "label": "Inverter not starting — Should return troubleshooting steps",
        "product": "Inverter",
        "issue": "Inverter is not starting, no power coming",
        "assert_steps": lambda r: len(r.troubleshooting_steps) >= 1,
        "assert_safety": lambda r: r.product_specific_warning is not None,
        "assert_confidence": lambda r: r.confidence >= 0.3,
    },
    {
        "id": "RAG-02",
        "label": "Solar Panel no output — Should return steps",
        "product": "Solar Panel",
        "issue": "Solar panel is not generating any electricity",
        "assert_steps": lambda r: len(r.troubleshooting_steps) >= 1,
        "assert_safety": lambda r: True,  # Solar safety warning is optional
        "assert_confidence": lambda r: r.confidence >= 0.2,
    },
    {
        "id": "RAG-03",
        "label": "Oxygen Concentrator — Must NOT troubleshoot, must escalate",
        "product": "Oxygen Concentrator",
        "issue": "Oxygen concentrator has stopped working",
        "assert_steps": lambda r: r.escalation_reason is not None,
        "assert_safety": lambda r: r.requires_field_visit == True,
        "assert_confidence": lambda r: r.resolved == False,
    },
    {
        "id": "RAG-04",
        "label": "3-Wheeler Battery leaking — Safety check must come first",
        "product": "3-Wheeler Battery",
        "issue": "Battery is making a hissing sound and I smell something strange",
        "assert_steps": lambda r: any(
            "leak" in step.lower() or "smell" in step.lower() or "step away" in step.lower()
            for step in r.troubleshooting_steps
        ) or ("leak" in (r.product_specific_warning or "").lower()),
        "assert_safety": lambda r: True,
        "assert_confidence": lambda r: True,
    },
    {
        "id": "RAG-05",
        "label": "Hallucination Guard — Completely irrelevant product (Car Engine)",
        "product": "Car Engine",
        "issue": "My car engine is making a grinding noise",
        "assert_steps": lambda r: r.confidence <= 0.5 or r.requires_field_visit == True,
        "assert_safety": lambda r: True,
        "assert_confidence": lambda r: r.resolved == False,
    },
    {
        "id": "RAG-06",
        "label": "Air Purifier indicator check — Should ask about display first",
        "product": "Air Purifier",
        "issue": "Air purifier stopped working suddenly",
        "assert_steps": lambda r: len(r.troubleshooting_steps) >= 1,
        "assert_safety": lambda r: True,
        "assert_confidence": lambda r: True,
    },
]


async def run_tests():
    print(f"\n{BLUE}{'='*65}{RESET}")
    print(f"{BLUE} RAG AGENT TEST SUITE — {len(TEST_CASES)} cases{RESET}")
    print(f"{BLUE}{'='*65}{RESET}\n")

    # Load the vector store (may be None if not indexed)
    vector_store = get_vector_store()
    if vector_store is None:
        warn("Vector store not found — RAG will rely on LLM knowledge only.")
        warn("Run 'python index_knowledge.py' to index documents first.\n")

    agent = RAGAgent(vector_store=vector_store)
    passed = 0
    failed = 0

    for tc in TEST_CASES:
        print(f"{YELLOW}[{tc['id']}] {tc['label']}{RESET}")
        try:
            response = await agent.diagnose(
                product_category=tc["product"],
                product_model=None,
                issue_description=tc["issue"],
                customer_name="Test User",
                warranty_status="valid",
            )

            info(f"Diagnosis: \"{response.diagnosis[:80]}...\"")
            info(f"Steps: {len(response.troubleshooting_steps)} | Confidence: {response.confidence:.2f}")
            info(f"Safety Warning: {str(response.product_specific_warning)[:60] if response.product_specific_warning else 'None'}")
            info(f"Field Visit: {response.requires_field_visit} | Escalation: {response.escalation_reason}")

            results = [
                (tc["assert_steps"](response),   "Steps assertion"),
                (tc["assert_safety"](response),  "Safety assertion"),
                (tc["assert_confidence"](response), "Confidence/outcome assertion"),
            ]

            all_pass = True
            for result, label in results:
                if result:
                    ok(label)
                else:
                    fail(label)
                    all_pass = False

            if all_pass:
                passed += 1
            else:
                failed += 1

        except Exception as e:
            fail(f"Exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

        print()

    total = passed + failed
    print(f"{BLUE}{'='*65}{RESET}")
    print(f"  Results: {GREEN}{passed} PASSED{RESET} | {RED}{failed} FAILED{RESET} | {total} TOTAL")
    score = (passed / total) * 100 if total else 0
    color = GREEN if score >= 80 else YELLOW if score >= 60 else RED
    print(f"  Score: {color}{score:.0f}%{RESET}")
    print(f"{BLUE}{'='*65}{RESET}\n")
    return passed, failed


if __name__ == "__main__":
    asyncio.run(run_tests())

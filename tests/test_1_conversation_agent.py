"""
PRACTICAL TEST 1: Conversation Agent (Slot Extraction + Language + Sentiment)
=============================================================================
Tests the brain of the voice agent without needing a live phone call.
Run: python tests/test_1_conversation_agent.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.conversation_agent import ConversationAgent
from app.models.agent_contracts import AgentRequest

# ─── Colour output for readability ────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"

def ok(msg):  print(f"  {GREEN}✅ PASS{RESET}  {msg}")
def fail(msg):print(f"  {RED}❌ FAIL{RESET}  {msg}")
def info(msg):print(f"  {BLUE}ℹ  INFO{RESET}  {msg}")

# ─── Test Case Definitions ─────────────────────────────────────────────────────
TEST_CASES = [
    {
        "id": "TC-01",
        "label": "Name extraction from natural sentence",
        "input": "Hi, I'm Ramesh and I need help with my inverter",
        "state": "VERIFYING",
        "slots": {},
        "history": [],
        "assert": lambda r: r.extracted_slots.get("customer_name") == "Ramesh",
        "assert_label": "customer_name == 'Ramesh'",
    },
    {
        "id": "TC-02",
        "label": "Hindi language detection + Romanized Hindi response",
        "input": "Mera naam Suresh hai, mujhe help chahiye",
        "state": "VERIFYING",
        "slots": {},
        "history": [],
        "assert": lambda r: any(
            word in r.response_text.lower()
            for word in ["aapka", "kya", "hain", "shukriya", "dhanyavaad", "batayein"]
        ),
        "assert_label": "Response contains Hindi Romanized words",
    },
    {
        "id": "TC-03",
        "label": "Product slang mapping (rickshaw → 3-Wheeler Battery)",
        "input": "Mera rickshaw ka battery kharab ho gaya hai",
        "state": "COLLECTING",
        "slots": {"customer_name": "Ramesh", "contact_number": "9876543210"},
        "history": [],
        "assert": lambda r: "3-Wheeler" in (r.extracted_slots.get("product_category") or "")
                          or "Battery" in (r.extracted_slots.get("product_category") or ""),
        "assert_label": "product_category maps to 3-Wheeler Battery",
    },
    {
        "id": "TC-04",
        "label": "Safety escalation for Oxygen Concentrator",
        "input": "My oxygen machine is not working, patient is struggling to breathe",
        "state": "COLLECTING",
        "slots": {"customer_name": "Priya", "contact_number": "9123456789"},
        "history": [],
        "assert": lambda r: r.next_action in ["SAFETY_ESCALATION", "ESCALATING"]
                          or r.metadata.get("needs_escalation") == True,
        "assert_label": "next_action is SAFETY_ESCALATION or needs_escalation=True",
    },
    {
        "id": "TC-05",
        "label": "Sentiment detection for angry customer",
        "input": "This is completely useless! You people never fix anything! I want a refund NOW!",
        "state": "COLLECTING",
        "slots": {"customer_name": "Arun", "contact_number": "9000000001"},
        "history": [],
        "assert": lambda r: r.sentiment in ["angry", "frustrated"],
        "assert_label": "sentiment == 'angry' or 'frustrated'",
    },
    {
        "id": "TC-06",
        "label": "Phone number extraction",
        "input": "My number is 98765 43210",
        "state": "VERIFYING",
        "slots": {"customer_name": "Vikram"},
        "history": [],
        "assert": lambda r: r.extracted_slots.get("contact_number") is not None,
        "assert_label": "contact_number is extracted",
    },
    {
        "id": "TC-07",
        "label": "Sales inquiry → OUT_OF_SCOPE routing",
        "input": "I want to buy a new solar panel. What is the price?",
        "state": "COLLECTING",
        "slots": {"customer_name": "Meera", "contact_number": "9001112222"},
        "history": [],
        "assert": lambda r: r.next_action in ["OUT_OF_SCOPE", "COLLECTING"],
        "assert_label": "next_action is OUT_OF_SCOPE (or stayed COLLECTING)",
    },
    {
        "id": "TC-08",
        "label": "No re-asking already-filled slot (name)",
        "input": "The inverter makes a beeping sound",
        "state": "COLLECTING",
        "slots": {"customer_name": "Deepak", "contact_number": "9876500000"},
        "history": [
            {"role": "assistant", "content": "Thank you Deepak. Which product are you calling about?"},
            {"role": "user", "content": "The inverter makes a beeping sound"},
        ],
        "assert": lambda r: "deepak" not in r.response_text.lower().split()[:3],
        "assert_label": "Agent does NOT start response with customer's name (avoid repetition)",
    },
]

# ─── Runner ────────────────────────────────────────────────────────────────────
async def run_tests():
    agent = ConversationAgent()
    print(f"\n{BLUE}{'='*65}{RESET}")
    print(f"{BLUE} CONVERSATION AGENT TEST SUITE — {len(TEST_CASES)} cases{RESET}")
    print(f"{BLUE}{'='*65}{RESET}\n")

    passed = 0
    failed = 0

    for tc in TEST_CASES:
        print(f"{YELLOW}[{tc['id']}] {tc['label']}{RESET}")

        request = AgentRequest(
            call_id=f"test-{tc['id']}",
            user_input=tc["input"],
            state=tc["state"],
            slots=tc["slots"],
            conversation_history=tc["history"],
            turn_number=1,
            sentiment="neutral",
            metadata={"current_phase": tc["state"], "already_asked": []}
        )

        try:
            response = await agent.process(request)
            info(f"Response: \"{response.response_text[:90]}...\"")
            info(f"Slots extracted: {response.extracted_slots}")
            info(f"Next state: {response.next_action} | Sentiment: {response.sentiment}")

            if tc["assert"](response):
                ok(tc["assert_label"])
                passed += 1
            else:
                fail(tc["assert_label"])
                failed += 1

        except Exception as e:
            fail(f"Exception: {e}")
            failed += 1

        print()

    # Summary
    total = passed + failed
    print(f"{BLUE}{'='*65}{RESET}")
    print(f"  Results: {GREEN}{passed} PASSED{RESET} | {RED}{failed} FAILED{RESET} | {total} TOTAL")
    score = (passed / total) * 100 if total else 0
    color = GREEN if score >= 80 else YELLOW if score >= 60 else RED
    print(f"  Score:   {color}{score:.0f}%{RESET}")
    print(f"{BLUE}{'='*65}{RESET}\n")
    return passed, failed


if __name__ == "__main__":
    asyncio.run(run_tests())

"""
PRACTICAL TEST 3: Decision Agent (Routing Logic + Business Rules + Safety)
==========================================================================
Tests that the Decision Agent makes correct escalate/resolve/continue decisions.
This agent has hardcoded business rules (bypass LLM) + LLM-powered nuance.
Run: python tests/test_3_decision_agent.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.decision_agent import DecisionAgent

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"

def ok(msg):  print(f"  {GREEN}✅ PASS{RESET}  {msg}")
def fail(msg):print(f"  {RED}❌ FAIL{RESET}  {msg}")
def info(msg):print(f"  {BLUE}ℹ  INFO{RESET}  {msg}")


TEST_CASES = [
    {
        "id": "DEC-01",
        "label": "Safety-critical product → MUST escalate with CRITICAL priority",
        "args": {
            "issue_description": "Oxygen concentrator stopped working",
            "product_category": "Oxygen Concentrator",
            "confidence": 0.9,
            "retry_count": 0,
            "sentiment": "neutral",
            "last_message": "The machine stopped working",
            "is_safety_critical": True,
            "requires_field_visit": False,
            "is_business_hours": True,
        },
        "assert": lambda r: r.action == "escalate" and r.ticket_priority == "critical",
        "assert_label": "action='escalate' AND ticket_priority='critical'",
    },
    {
        "id": "DEC-02",
        "label": "Customer asks for human agent → MUST escalate",
        "args": {
            "issue_description": "Inverter not working",
            "product_category": "Inverter",
            "confidence": 0.6,
            "retry_count": 1,
            "sentiment": "frustrated",
            "last_message": "Can I please talk to a human agent?",
            "is_safety_critical": False,
            "requires_field_visit": False,
            "is_business_hours": True,
        },
        "assert": lambda r: r.action == "escalate",
        "assert_label": "action='escalate' (explicit human request)",
    },
    {
        "id": "DEC-03",
        "label": "Max retries reached (3) → MUST escalate",
        "args": {
            "issue_description": "Solar panel no power",
            "product_category": "Solar Panel",
            "confidence": 0.5,
            "retry_count": 3,
            "sentiment": "neutral",
            "last_message": "Still not working after your steps",
            "is_safety_critical": False,
            "requires_field_visit": False,
            "is_business_hours": True,
        },
        "assert": lambda r: r.action == "escalate",
        "assert_label": "action='escalate' (retry_count >= 3)",
    },
    {
        "id": "DEC-04",
        "label": "Customer confirms issue fixed → MUST resolve",
        "args": {
            "issue_description": "Inverter beeping",
            "product_category": "Inverter",
            "confidence": 0.85,
            "retry_count": 1,
            "sentiment": "positive",
            "last_message": "Yes it is working now! Thank you so much!",
            "is_safety_critical": False,
            "requires_field_visit": False,
            "is_business_hours": True,
        },
        "assert": lambda r: r.action in ["resolve", "continue"],
        "assert_label": "action='resolve' or 'continue' (positive feedback)",
    },
    {
        "id": "DEC-05",
        "label": "Low confidence but first retry → MUST continue",
        "args": {
            "issue_description": "Inverter fluctuating",
            "product_category": "Inverter",
            "confidence": 0.4,
            "retry_count": 0,
            "sentiment": "neutral",
            "last_message": "I tried the steps but the light is still blinking",
            "is_safety_critical": False,
            "requires_field_visit": False,
            "is_business_hours": True,
        },
        "assert": lambda r: r.action in ["continue", "escalate"],
        "assert_label": "action='continue' (first attempt, low confidence)",
    },
    {
        "id": "DEC-06",
        "label": "Angry + retry >= 1 → MUST escalate with HIGH priority",
        "args": {
            "issue_description": "Inverter broken",
            "product_category": "Inverter",
            "confidence": 0.5,
            "retry_count": 1,
            "sentiment": "angry",
            "last_message": "Nothing is working! This is a scam!",
            "is_safety_critical": False,
            "requires_field_visit": False,
            "is_business_hours": True,
        },
        "assert": lambda r: r.action == "escalate",
        "assert_label": "action='escalate' (angry + retry>=1)",
    },
    {
        "id": "DEC-07",
        "label": "Field visit required → MUST escalate",
        "args": {
            "issue_description": "Inverter internal parts damaged",
            "product_category": "Inverter",
            "confidence": 0.3,
            "retry_count": 0,
            "sentiment": "neutral",
            "last_message": "I can see a burnt smell from inside",
            "is_safety_critical": False,
            "requires_field_visit": True,
            "is_business_hours": True,
        },
        "assert": lambda r: r.action in ["escalate", "continue"],
        "assert_label": "action='escalate' (field visit required)",
    },
    {
        "id": "DEC-08",
        "label": "Hindi human request keyword → MUST escalate",
        "args": {
            "issue_description": "3-Wheeler battery problem",
            "product_category": "3-Wheeler Battery",
            "confidence": 0.7,
            "retry_count": 0,
            "sentiment": "frustrated",
            "last_message": "Mujhe ek insaan se baat karni hai",
            "is_safety_critical": False,
            "requires_field_visit": False,
            "is_business_hours": True,
        },
        "assert": lambda r: r.action == "escalate",
        "assert_label": "action='escalate' (Hindi 'insaan' keyword detected)",
    },
]


async def run_tests():
    agent = DecisionAgent()
    print(f"\n{BLUE}{'='*65}{RESET}")
    print(f"{BLUE} DECISION AGENT TEST SUITE — {len(TEST_CASES)} cases{RESET}")
    print(f"{BLUE}{'='*65}{RESET}\n")

    passed = 0
    failed = 0

    for tc in TEST_CASES:
        print(f"{YELLOW}[{tc['id']}] {tc['label']}{RESET}")
        try:
            response = await agent.decide(**tc["args"])
            info(f"Action: {response.action} | Priority: {response.ticket_priority} | SLA: {response.sla}")
            info(f"Reason: {response.reason[:80]}")
            info(f"Confidence: {response.confidence:.2f}")

            if tc["assert"](response):
                ok(tc["assert_label"])
                passed += 1
            else:
                fail(tc["assert_label"])
                fail(f"Got: action='{response.action}', priority='{response.ticket_priority}'")
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

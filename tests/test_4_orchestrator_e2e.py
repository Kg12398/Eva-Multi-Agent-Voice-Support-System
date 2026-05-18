"""
PRACTICAL TEST 4: Full Orchestrator End-to-End (Multi-Turn Call Simulation)
============================================================================
Simulates a REAL multi-turn call from Greeting → Verifying → Collecting →
Troubleshooting → Escalation, checking state transitions at each step.
Requires: Redis running locally (redis-server)
Run: python tests/test_4_orchestrator_e2e.py
"""

import asyncio
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.orchestrator import Orchestrator
from app.services.redis_service import redis_service
from app.utils.rag_loader import get_vector_store

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
RESET  = "\033[0m"

def ok(msg):    print(f"  {GREEN}✅ PASS{RESET}  {msg}")
def fail(msg):  print(f"  {RED}❌ FAIL{RESET}  {msg}")
def info(msg):  print(f"  {BLUE}ℹ  INFO{RESET}  {msg}")
def gauri(msg): print(f"\n  {CYAN}🎙 Gauri:{RESET} {msg}\n")
def user(msg):  print(f"  {YELLOW}👤 User:{RESET}  {msg}")


# ─── Scenario 1: Happy Path (English) ────────────────────────────────────────
SCENARIO_1 = {
    "id": "E2E-01",
    "label": "Happy Path: English Inverter Support → Ticket Created",
    "turns": [
        {
            "user": "My name is Rahul Sharma",
            "expect_state": ["VERIFYING", "COLLECTING"],
            "expect_in_response": ["rahul", "number", "phone", "mobile", "contact"],
        },
        {
            "user": "My number is 9876543210",
            "expect_state": ["VERIFYING", "COLLECTING"],
            "expect_in_response": ["inverter", "product", "help", "what", "issue", "problem"],
        },
        {
            "user": "My inverter is not working, it shows a red light",
            "expect_state": ["COLLECTING", "TROUBLESHOOTING", "READY_FOR_DIAGNOSIS"],
            "expect_in_response": ["step", "check", "press", "light", "try"],
        },
        {
            "user": "I tried the steps but it's still not working",
            "expect_state": ["TROUBLESHOOTING", "DECISION", "ESCALATION", "END"],
            "expect_in_response": ["ticket", "team", "contact", "hour", "engineer"],
        },
    ],
}

# ─── Scenario 2: Hindi Caller ─────────────────────────────────────────────────
SCENARIO_2 = {
    "id": "E2E-02",
    "label": "Hindi Caller: Language Anchoring Test",
    "turns": [
        {
            "user": "Hindi",
            "expect_state": ["VERIFYING"],
            "expect_in_response": ["naam", "aapka", "kya", "hain", "shukriya", "please", "name", "namaste"],
        },
        {
            "user": "Mera naam Suresh hai",
            "expect_state": ["VERIFYING"],
            "expect_in_response": ["number", "mobile", "numb", "phone", "registered"],
        },
    ],
}

# ─── Scenario 3: Safety Escalation ───────────────────────────────────────────
SCENARIO_3 = {
    "id": "E2E-03",
    "label": "Safety Escalation: Oxygen Concentrator → Emergency Ticket",
    "turns": [
        {
            "user": "Priya",
            "expect_state": ["VERIFYING"],
            "expect_in_response": [],
        },
        {
            "user": "9123456780",
            "expect_state": ["VERIFYING", "COLLECTING"],
            "expect_in_response": [],
        },
        {
            "user": "My oxygen concentrator machine is not working. Patient is very sick.",
            "expect_state": ["SAFETY_ESCALATION", "END", "ESCALATION"],
            "expect_in_response": ["emergency", "1 hour", "ticket", "medical", "team", "priority"],
        },
    ],
}


async def run_scenario(orchestrator, scenario):
    call_id = f"test-{scenario['id']}-{int(time.time())}"
    print(f"\n{BLUE}── {scenario['id']}: {scenario['label']} {'─'*30}{RESET}")

    # Start the call
    greeting = await orchestrator.start_call(call_id)
    gauri(greeting[:120])

    turn_pass = 0
    turn_fail = 0

    for i, turn in enumerate(scenario["turns"], 1):
        print(f"  {YELLOW}--- Turn {i} ---{RESET}")
        user(turn["user"])

        start = time.time()
        response = await orchestrator.process_turn(call_id, turn["user"])
        elapsed = (time.time() - start) * 1000

        gauri(response[:150] + ("..." if len(response) > 150 else ""))

        # Check 1: Response latency
        if elapsed < 5000:
            ok(f"Latency: {elapsed:.0f}ms < 5000ms")
        else:
            fail(f"Latency: {elapsed:.0f}ms > 5000ms (too slow)")

        # Check 2: Response text expectations
        if turn["expect_in_response"]:
            response_lower = response.lower()
            matched = any(kw in response_lower for kw in turn["expect_in_response"])
            if matched:
                ok(f"Response contains expected keyword from {turn['expect_in_response'][:3]}")
                turn_pass += 1
            else:
                fail(f"Response missing expected keywords: {turn['expect_in_response']}")
                turn_fail += 1
        else:
            info("No keyword assertions for this turn")
            turn_pass += 1

        # Get session state from Redis
        try:
            session = await redis_service.get_session(call_id)
            if session:
                state_str = session.state.value if hasattr(session.state, 'value') else str(session.state)
                info(f"FSM State: {state_str} | Turn: {session.turn_count} | Sentiment: {session.sentiment}")

                if turn["expect_state"]:
                    if state_str in turn["expect_state"]:
                        ok(f"State '{state_str}' is in expected {turn['expect_state']}")
                    else:
                        fail(f"State '{state_str}' NOT in expected {turn['expect_state']}")
                        turn_fail += 1

                # Show slots filled so far
                filled = {k: v for k, v in session.slots.model_dump().items()
                         if v is not None and k not in ["already_asked", "question_just_asked"]}
                if filled:
                    info(f"Filled Slots: {filled}")
        except Exception as e:
            info(f"Could not read session: {e}")

        print()

    # Cleanup
    try:
        await redis_service.delete_session(call_id)
    except:
        pass

    return turn_pass, turn_fail


async def run_tests():
    print(f"\n{BLUE}{'='*65}{RESET}")
    print(f"{BLUE} ORCHESTRATOR END-TO-END TEST SUITE (3 Scenarios){RESET}")
    print(f"{BLUE}{'='*65}{RESET}")
    print(f"\n  {YELLOW}⚠ Requires Redis to be running: redis-server{RESET}")
    print(f"  {YELLOW}⚠ Each turn calls the real Groq LLM — expect 1-3s per turn{RESET}\n")

    # Init services
    await redis_service.connect()
    vector_store = get_vector_store()
    orchestrator = Orchestrator(vector_store=vector_store)

    total_pass = 0
    total_fail = 0

    for scenario in [SCENARIO_1, SCENARIO_2, SCENARIO_3]:
        try:
            p, f = await run_scenario(orchestrator, scenario)
            total_pass += p
            total_fail += f
        except Exception as e:
            print(f"\n{RED}Scenario {scenario['id']} crashed: {e}{RESET}")
            import traceback
            traceback.print_exc()
            total_fail += 1

    await redis_service.disconnect()

    total = total_pass + total_fail
    print(f"\n{BLUE}{'='*65}{RESET}")
    print(f"  E2E Results: {GREEN}{total_pass} PASSED{RESET} | {RED}{total_fail} FAILED{RESET} | {total} TOTAL")
    score = (total_pass / total) * 100 if total else 0
    color = GREEN if score >= 80 else YELLOW if score >= 60 else RED
    print(f"  Score: {color}{score:.0f}%{RESET}")
    print(f"{BLUE}{'='*65}{RESET}\n")


if __name__ == "__main__":
    asyncio.run(run_tests())

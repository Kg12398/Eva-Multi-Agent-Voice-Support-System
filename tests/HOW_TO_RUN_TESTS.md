# 🧪 PRACTICAL TESTING GUIDE — GAURI VOICE AGENT
## Run Real Tests, Get Real Results, Defend in Any Interview

---

## 📁 Test Files Created
```
voice_agent/
└── tests/
    ├── test_1_conversation_agent.py   ← 8 unit tests (slots, language, sentiment)
    ├── test_2_rag_agent.py            ← 6 tests (retrieval, safety, hallucination)
    ├── test_3_decision_agent.py       ← 8 tests (routing rules, escalation logic)
    ├── test_4_orchestrator_e2e.py     ← 3 full call simulations (Redis required)
    ├── test_5_latency_and_security.py ← Latency + PII masking + prompt injection
    └── run_all_tests.py               ← Runs all 5 suites & prints master summary
```

---

## ⚡ HOW TO RUN (Step by Step)

### Step 1: Activate your virtual environment
```powershell
cd C:\Users\dell\Project\voice_agent
.\.venv\Scripts\Activate.ps1
```

### Step 2: Run each test individually (start here)
```powershell
# Test 1 — Conversation Agent (no Redis needed)
python tests/test_1_conversation_agent.py

# Test 2 — RAG Agent (no Redis needed)
python tests/test_2_rag_agent.py

# Test 3 — Decision Agent (no Redis needed)
python tests/test_3_decision_agent.py

# Test 4 — Full E2E (Redis MUST be running)
# Start Redis first: see Step 3 below
python tests/test_4_orchestrator_e2e.py

# Test 5 — Latency & Security (no Redis needed)
python tests/test_5_latency_and_security.py
```

### Step 3: Start Redis (for Test 4)
```powershell
# Option A: If Redis is installed
redis-server

# Option B: Using Docker
docker run -d -p 6379:6379 redis:alpine
```

### Step 4: Run the full master suite
```powershell
python tests/run_all_tests.py
```

---

## 📊 WHAT EACH TEST PROVES (For Interviews)

| Test File | What It Proves | Interview Claim |
|:---|:---|:---|
| `test_1` | Slot extraction, Hindi detection, safety routing | "I validated slot extraction across 8 scenarios" |
| `test_2` | RAG grounding, hallucination prevention | "I tested RAG faithfulness with safety guardrails" |
| `test_3` | All 8 decision routing rules | "Decision logic is deterministic and unit-tested" |
| `test_4` | Full call lifecycle with state transitions | "I simulated 3 real call scenarios end-to-end" |
| `test_5` | Latency budget + PII + injection resistance | "I profiled latency and hardened security" |

---

## 🗣️ HOW TO TALK ABOUT RESULTS IN INTERVIEW

After you run the tests, you can say:

> *"I built a comprehensive test suite with 35+ test cases across 5 layers:
> unit tests per agent, end-to-end call simulations, latency profiling, 
> PII masking validation, and prompt injection resistance.
> For example, in the Decision Agent tests, I verified that an Oxygen 
> Concentrator call always produces a CRITICAL priority ticket within
> one LLM call — because that rule is hardcoded, not LLM-dependent."*

---

## ⚠️ TROUBLESHOOTING

**If you see `ModuleNotFoundError: No module named 'langchain_groq'`:**
```powershell
pip install langchain-groq
```

**If you see `GROQ_API_KEY not set`:**
Make sure your `.env` file has `GROQ_API_KEY=gsk_xxx...` set.

**If Test 4 fails with `Connection refused`:**
Redis is not running. Use `docker run -d -p 6379:6379 redis:alpine`

**If RAG tests show `Vector store not found`:**
```powershell
python index_knowledge.py
```

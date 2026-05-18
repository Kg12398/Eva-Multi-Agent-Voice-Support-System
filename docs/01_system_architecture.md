# Multi-Agent Voice Service Support System — System Architecture

## 1. End-to-End Call Flow

```
┌──────────────┐     ┌────────────────────┐     ┌──────────────────────┐
│   Customer   │────▶│   Twilio           │────▶│   LiveKit            │
│   Phone      │PSTN │   Phone Number     │ SIP │   SIP Bridge         │
│              │     │   + SIP Trunk      │Trunk│   (SIP → WebRTC)     │
└──────────────┘     └────────────────────┘     └──────────┬───────────┘
                                                           │
                                                           ▼
                                                ┌──────────────────────┐
                                                │   LiveKit Room       │
                                                │                      │
                                                │  ┌────────────────┐  │
                                                │  │ Silero VAD     │  │
                                                │  │ (speech detect)│  │
                                                │  └───────┬────────┘  │
                                                │          │           │
                                                │  ┌───────▼────────┐  │
                                                │  │ Deepgram STT   │  │
                                                │  │ (streaming)    │  │
                                                │  └───────┬────────┘  │
                                                │          │           │
                                                │  ┌───────▼────────┐  │
                                                │  │ LangGraph      │  │
                                                │  │ Orchestrator   │  │
                                                │  │ + Gemini Flash │  │
                                                │  └───────┬────────┘  │
                                                │          │           │
                                                │  ┌───────▼────────┐  │
                                                │  │ Deepgram TTS   │  │
                                                │  │ (streaming)    │  │
                                                │  └───────┬────────┘  │
                                                │          │           │
                                                │          ▼           │
                                                │   Audio back to     │
                                                │   caller via WebRTC │
                                                └──────────────────────┘
```

## 2. Component Stack (Locked)

| Layer | Component | Role |
|-------|-----------|------|
| **Telephony** | Twilio Phone Number | Provides a callable phone number (PSTN) |
| **Telephony** | Twilio Elastic SIP Trunk | Bridges PSTN call → SIP protocol → forwards to LiveKit |
| **Real-Time Media** | LiveKit SIP Bridge | Receives SIP trunk, converts to WebRTC stream |
| **Real-Time Media** | LiveKit Room + Agents SDK | Manages the audio room, hosts our AI agent |
| **VAD** | Silero VAD | Detects speech vs silence, triggers STT only on speech |
| **STT** | Deepgram Nova-2 (streaming) | Real-time audio → text transcription |
| **LLM** | Gemini 2.5 Flash | Reasoning, slot extraction, response generation |
| **TTS** | Deepgram Aura (streaming) | Text → natural speech audio (cost-effective) |
| **Agent Framework** | LangGraph | State machine orchestrator for multi-agent routing |
| **Session State** | Redis | Fast in-memory session + slot storage per call |
| **Database** | PostgreSQL | Call logs, transcripts, tickets, analytics |
| **Storage** | AWS S3 | Raw audio recordings archive |
| **Observability** | Langfuse | LLM call tracing, latency monitoring, cost tracking |
| **Backend** | FastAPI | REST API for dashboard, health checks, admin |

## 3. Twilio SIP Trunk → LiveKit Integration (Critical Path)

### Setup Steps:
1. **Buy a Twilio Phone Number** (local or toll-free)
2. **Create an Elastic SIP Trunk** in Twilio Console
3. **Configure Origination URI** → point to LiveKit SIP Bridge URL
   - Example: `sip:your-livekit-instance.livekit.cloud`
4. **LiveKit SIP Bridge** receives the incoming SIP INVITE
5. **LiveKit creates a Room** and places the caller as a participant
6. **Our AI Agent** (Python, using `livekit-agents` SDK) auto-joins the room
7. **Bidirectional audio** flows: caller ↔ LiveKit Room ↔ AI Agent

### Key Configuration:
```
Twilio SIP Trunk:
  ├── Origination URI: sip:<livekit-sip-bridge-url>
  ├── Authentication: IP ACL or Credential List
  └── Call Control: Webhooks for status callbacks

LiveKit SIP Bridge:
  ├── Inbound Trunk Config: accepts calls from Twilio IP ranges
  ├── Dispatch Rule: routes to our agent worker
  └── Room Settings: auto-create room per call
```

## 4. Multi-Agent Topology (Revised)

### LLM-Powered Agents (require reasoning):
| Agent | Purpose | When Called |
|-------|---------|-------------|
| **Conversation Agent** | Single LLM call → extracts slots + generates response + detects sentiment | Every user turn |
| **RAG/Diagnosis Agent** | Queries ChromaDB knowledge base + reasons over troubleshooting steps | When issue is identified |
| **Decision Agent** | Determines: continue troubleshooting vs escalate | After diagnosis attempt |

### Tool Functions (no LLM, simple logic):
| Function | Purpose | Latency |
|----------|---------|---------|
| `warranty_lookup()` | DB query by serial number | <10ms |
| `ticket_create()` | Inserts structured ticket into PostgreSQL | <20ms |

### Background Services (async, non-blocking):
| Service | Purpose |
|---------|---------|
| Call Logger | Writes transcript + metadata to PostgreSQL |
| Summary Generator | Post-call LLM summarization |
| Audio Archiver | Uploads raw audio to S3 |

## 5. State Machine (Slot-Driven FSM via LangGraph)

```
                    ┌─────────────┐
                    │  GREETING   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
               ┌────│  COLLECTING │◄───────────┐
               │    │  (dynamic)  │            │
               │    └──────┬──────┘            │
               │           │                   │
               │    All slots filled?          │
               │    ┌──YES──┴──NO──┐           │
               │    │              │           │
               │    ▼              └───────────┘
               │  ┌──────────────┐   (ask for missing slot)
               │  │  VALIDATING  │
               │  └──────┬───────┘
               │         │
               │  ┌──────▼───────┐
               │  │CHECK_WARRANTY│  ← warranty_lookup() tool
               │  └──────┬───────┘
               │         │
               │  ┌──────▼───────┐
               │  │  DIAGNOSIS   │  ← RAG Agent (ChromaDB)
               │  └──────┬───────┘
               │         │
               │  ┌──────▼───────┐
               │  │  DECISION    │  ← Decision Agent
               │  └───┬──────┬───┘
               │      │      │
               │ Resolved  Escalate
               │      │      │
               │  ┌───▼──┐ ┌─▼─────────┐
               │  │CLOSE │ │ESCALATION  │ ← ticket_create() + optional warm transfer
               │  └──────┘ └────────────┘
               │
               │ (user corrects info)
               └──────────────────────────┘
```

### Slot-Based Memory (stored in Redis):
```json
{
  "call_id": "uuid",
  "state": "COLLECTING",
  "slots": {
    "customer_name": null,
    "product_category": null,
    "model": null,
    "serial_number": null,
    "issue_description": null
  },
  "warranty_status": null,
  "diagnosis_result": null,
  "sentiment": "neutral",
  "turn_count": 0,
  "conversation_history": [],
  "created_at": "ISO timestamp"
}
```

## 6. Latency Budget (Target: < 2000ms per turn)

| Component | Budget (ms) | Notes |
|-----------|------------|-------|
| Silero VAD (endpointing) | 100-200 | Wait after silence before triggering |
| Deepgram STT (streaming) | 200-300 | Streaming, near real-time |
| Network overhead | 50-100 | To/from LLM API |
| Gemini Flash (1 call) | 400-700 | Streaming first token |
| Deepgram TTS (first byte) | 200-300 | Streaming audio generation |
| LiveKit audio playout | 50-100 | WebRTC back to caller |
| **TOTAL** | **1000-1700ms** | ✅ Within budget |

## 7. Critical Production Features

- **Barge-in Handling:** If user speaks during TTS → immediately stop TTS, process new input
- **Endpointing:** Silero VAD + Deepgram `utterance_end_ms` (700ms silence = user done speaking)
- **Circuit Breakers:** Retry + fallback for every external API (Deepgram, Gemini, TTS)
- **Audio Recording:** Raw call audio archived to S3 for QA/compliance
- **Call Recording Consent:** "This call may be recorded for quality purposes" at start
- **Max Turn Limit:** 20 turns, then graceful escalation
- **Health Check Endpoint:** `/health` verifying all dependencies

# 📋 Pre-Build Checklist: Everything You Need Before We Start

> **Project:** Multi-Agent Voice Service Support System
> **Build Location:** `c:\Users\dell\Project\voice_agent\`
> **Target Start:** Tomorrow (April 9, 2026)

---

## 🔴 TIER 1 — Must Have BEFORE Day 1 (Tomorrow)

These are blocking. We literally cannot write a single line of working code without them.

### 1.1 API Keys & Accounts

| # | Service | What You Need | How to Get It | Free Tier? |
|---|---------|--------------|---------------|------------|
| 1 | **Twilio** | Account SID + Auth Token + Phone Number | [twilio.com/try-twilio](https://www.twilio.com/try-twilio) | ✅ Trial gives $15 credit + free number |
| 2 | **LiveKit** | API Key + API Secret + Cloud URL | [cloud.livekit.io](https://cloud.livekit.io) | ✅ Free tier: 50 monthly participants |
| 3 | **Deepgram** | API Key | [console.deepgram.com](https://console.deepgram.com) | ✅ $200 free credit |
| 4 | **Google Gemini** | API Key (for Gemini 2.5 Flash) | [aistudio.google.com/apikey](https://aistudio.google.com/app/apikey) | ✅ Generous free tier |
| 5 | **ElevenLabs** | API Key | [elevenlabs.io](https://elevenlabs.io) | ✅ Free tier: 10,000 chars/month |

> [!TIP]
> **You can sign up for ALL of these in ~30 minutes.** Every single one has a free tier that's more than enough for development and testing. You won't spend a single rupee until we go to production.

### 1.2 Business Decisions (I Need YOUR Input)

These are decisions only YOU can make. I need answers to build the system correctly.

#### A. Company & Product Information

| # | Question | Example Answer | Your Answer |
|---|----------|---------------|-------------|
| 1 | **What is your company name?** | "TechNova Solutions" | ___________ |
| 2 | **What industry are you in?** | Electronics / SaaS / Telecom / etc. | ___________ |
| 3 | **What products/services do customers call about?** | Routers, Laptops, Software subscriptions | ___________ |
| 4 | **List 3-5 product categories** | ["Routers", "Modems", "Smart Home Devices"] | ___________ |

#### B. Support Scenarios (What Issues Do Customers Call About?)

| # | Question | Example Answer | Your Answer |
|---|----------|---------------|-------------|
| 5 | **Top 5 most common customer issues** | WiFi dropping, billing dispute, password reset, device not turning on, slow speed | ___________ |
| 6 | **Do you have warranty on products? How is it checked?** | Yes, by serial number, 1-year standard | ___________ |
| 7 | **What information do you need from the caller?** | Name, phone, product model, serial number, issue description | ___________ |
| 8 | **When should the AI escalate to a human?** | After 2 failed troubleshooting attempts, or if user requests it | ___________ |

#### C. Voice & Brand Personality

| # | Question | Example Answer | Your Answer |
|---|----------|---------------|-------------|
| 9 | **What tone should the AI use?** | Professional but warm / Casual and friendly / Strictly formal | ___________ |
| 10 | **What should the AI's name be?** | "Nova" / "Alex" / "Support Assistant" | ___________ |
| 11 | **Greeting message?** | "Hi, thank you for calling TechNova. My name is Nova, how can I help you today?" | ___________ |
| 12 | **Preferred language?** | English only / Hindi + English / Multilingual | ___________ |

#### D. Escalation & Ticketing

| # | Question | Example Answer | Your Answer |
|---|----------|---------------|-------------|
| 13 | **Where should tickets go?** | Email / Slack / Jira / Custom dashboard | ___________ |
| 14 | **Do you have human agents to transfer to?** | Yes (provide their phone numbers later) / No, ticket only | ___________ |
| 15 | **Business hours?** | 24/7 / 9 AM - 6 PM IST / Custom | ___________ |

---

## 🟡 TIER 2 — Must Have Before End of Week 1

We can start building without these, but we'll need them before the system is fully functional.

### 2.1 Infrastructure Accounts

| # | Service | What You Need | Why |
|---|---------|--------------|-----|
| 6 | **AWS Account** | Access Key + Secret + S3 Bucket | For storing audio recordings |
| 7 | **PostgreSQL** | Connection string | For call logs, tickets, analytics. Can use free [Supabase](https://supabase.com) or [Neon](https://neon.tech) |
| 8 | **Redis** | Connection string | For session state. Can use free [Upstash](https://upstash.com) (10K commands/day free) |
| 9 | **Langfuse** | API Key | For LLM observability. Free self-hosted or [cloud.langfuse.com](https://cloud.langfuse.com) |

### 2.2 Knowledge Base Content

This is the data your RAG Agent will use to troubleshoot issues. You need to provide:

| # | Content Type | Format | Example |
|---|-------------|--------|---------|
| 1 | **Product manuals / user guides** | PDF, DOCX, or TXT | Router_AX5200_Manual.pdf |
| 2 | **Troubleshooting guides** | PDF, DOCX, or TXT | Troubleshooting_WiFi_Issues.pdf |
| 3 | **FAQ document** | Any text format | "Q: How do I reset? A: Hold button 10 sec..." |
| 4 | **Product catalog** | CSV or JSON | product_name, model, category, warranty_period |

> [!IMPORTANT]
> **If you don't have formal documents yet, no problem!** We can start with a simple FAQ JSON file that you fill in. I'll create a template for you. We can add proper PDFs later.

---

## 🟢 TIER 3 — Nice to Have (Can Add Later)

| # | Item | Purpose |
|---|------|---------|
| 1 | Custom domain | For hosting the dashboard (e.g., support.yourcompany.com) |
| 2 | Human agent phone numbers | For live Twilio warm-transfer escalation |
| 3 | Existing CRM/ticketing system API | For integrating ticket creation into existing workflows |
| 4 | Company logo + brand colors | For the monitoring dashboard UI |
| 5 | SSL certificates | For production HTTPS (auto-generated via Let's Encrypt) |

---

## 💰 Expected Monthly Cost (at 50 calls/day)

| Service | Monthly Est. | Notes |
|---------|-------------|-------|
| Twilio | ~₹3,200 ($38) | Inbound phone number + minutes |
| LiveKit Cloud | ~₹1,500 ($18) | Real-time media streaming |
| Deepgram STT | ~₹1,600 ($19) | Streaming transcription |
| ElevenLabs TTS | ~₹9,000 ($108) | Premium voice synthesis (can reduce with Deepgram TTS) |
| Gemini Flash | ~₹170 ($2) | LLM reasoning |
| Redis (Upstash) | ₹0 - ₹1,250 | Free tier likely sufficient |
| PostgreSQL (Neon) | ₹0 - ₹1,250 | Free tier likely sufficient |
| AWS S3 | ~₹85 ($1) | Audio storage |
| **TOTAL** | **~₹16,800/mo (~$200)** | At 50 calls/day, 3 min avg |

> [!TIP]
> **During development, your cost will be ₹0** since all services have free tiers. You only pay when you go to production scale.

---

## 🚀 Day 1 Build Plan (Once You Provide Tier 1 Inputs)

Here's exactly what we'll build tomorrow:

```
voice_agent/
├── .env                          # All API keys (gitignored)
├── .gitignore                    # Security
├── requirements.txt              # All Python dependencies
├── README.md                     # Project documentation
│
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # Settings & environment loading
│   │
│   ├── voice_pipeline/
│   │   ├── __init__.py
│   │   ├── livekit_worker.py     # LiveKit agent worker (VAD + STT + TTS loop)
│   │   ├── stt_handler.py        # Deepgram streaming integration
│   │   ├── tts_handler.py        # ElevenLabs streaming integration
│   │   └── barge_in.py           # Interruption handler
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # LangGraph state machine (the brain)
│   │   ├── conversation_agent.py # Single LLM call: extract + respond + sentiment
│   │   ├── rag_agent.py          # Knowledge base lookup + reasoning
│   │   └── decision_agent.py     # Resolve vs escalate logic
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── warranty_lookup.py    # Simple DB/API function
│   │   ├── ticket_creator.py     # Structured ticket creation
│   │   └── sentiment_classifier.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── call_state.py         # Pydantic models for call state
│   │   ├── agent_contracts.py    # Request/Response schemas
│   │   └── database_models.py    # SQLAlchemy ORM models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── redis_service.py      # Session state management
│   │   ├── db_service.py         # PostgreSQL operations
│   │   └── s3_service.py         # Audio recording storage
│   │
│   └── utils/
│       ├── __init__.py
│       ├── circuit_breaker.py    # Fault tolerance
│       ├── logger.py             # Structured logging
│       └── constants.py          # System prompts, configs
│
├── knowledge_base/
│   ├── documents/                # Your product PDFs/docs go here
│   └── faq.json                  # Quick-start FAQ template
│
├── tests/
│   ├── test_orchestrator.py
│   ├── test_voice_pipeline.py
│   └── test_agents.py
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
└── scripts/
    ├── setup_twilio_sip.py       # Auto-configure Twilio SIP trunk
    └── seed_knowledge_base.py    # Load docs into vector DB
```

---

## ✅ YOUR ACTION ITEMS FOR TONIGHT

1. **Sign up** for all 5 services in Tier 1.1 (takes ~30 min)
2. **Answer** all 15 questions in Tier 1.2 (takes ~10 min)
3. **Gather** any product docs/FAQs you have (even rough drafts are fine)

Once you share the answers tomorrow, we start building immediately. No further planning needed — we go straight to code. 🔥

# 💰 Cost Breakdown: 5 Calls/Day (150 Calls/Month)

## Assumptions

| Parameter | Value |
|-----------|-------|
| Calls per day | 5 |
| Days per month | 30 |
| **Total calls/month** | **150** |
| Avg call duration | 3 minutes |
| **Total call minutes/month** | **450 minutes** |
| AI speaking time per call | ~1.5 minutes (half the call) |
| AI speaking chars per call | ~1,350 characters (~225 words) |
| Total TTS chars/month | ~202,500 characters |
| LLM turns per call | ~8 |
| USD to INR rate | ₹84 |

---

## Option A: With ElevenLabs TTS (Premium Voice Quality)

| # | Service | Calculation | Monthly (USD) | Monthly (INR) |
|---|---------|-------------|---------------|----------------|
| 1 | **Twilio** (phone number + minutes) | $1.15 number + 450 min × $0.0085 | **$5.00** | ₹420 |
| 2 | **LiveKit Cloud** (audio streaming) | 450 min × $0.004/min | **$1.80** | ₹151 |
| 3 | **Deepgram STT** (transcription) | 450 min × $0.0043/min | **$1.94** | ₹163 |
| 4 | **Gemini 2.5 Flash** (LLM) | 150 calls × ~20K tokens = 3M tokens | **$0.72** | ₹60 |
| 5 | **ElevenLabs TTS** | 202K chars → Creator Plan needed | **$22.00** | ₹1,848 |
| 6 | **Redis** (Upstash) | 250 commands/day → Free tier | **$0** | ₹0 |
| 7 | **PostgreSQL** (Neon/Supabase) | 150 records/month → Free tier | **$0** | ₹0 |
| 8 | **AWS S3** (audio storage) | ~450 MB/month → negligible | **$0.01** | ₹1 |
| 9 | **Langfuse** (observability) | Free cloud tier (50K obs/month) | **$0** | ₹0 |
| | | | | |
| | **TOTAL (Option A)** | | **~$31.50/mo** | **~₹2,650/mo** |

> ⚠️ ElevenLabs alone is **70% of your total cost**. Their Creator plan ($22/mo) gives 100K chars but you need ~202K chars. You'd need to either:
> - Buy the **Pro plan ($99/mo)** — overkill and expensive
> - Use the **Creator plan + pay $0.30/1000 overage chars** → $22 + $30.75 = ~$53/mo
> - Or switch to **Option B** below 👇

---

## ⭐ Option B: With Deepgram TTS (Recommended for Cost Savings)

Deepgram's Aura TTS is high quality and **20x cheaper** than ElevenLabs.

| # | Service | Calculation | Monthly (USD) | Monthly (INR) |
|---|---------|-------------|---------------|----------------|
| 1 | **Twilio** | Same as above | **$5.00** | ₹420 |
| 2 | **LiveKit Cloud** | Same as above | **$1.80** | ₹151 |
| 3 | **Deepgram STT** | Same as above | **$1.94** | ₹163 |
| 4 | **Gemini 2.5 Flash** | Same as above | **$0.72** | ₹60 |
| 5 | **Deepgram TTS (Aura)** | 225 min × $0.0065/min | **$1.46** | ₹123 |
| 6 | **Redis** | Free tier | **$0** | ₹0 |
| 7 | **PostgreSQL** | Free tier | **$0** | ₹0 |
| 8 | **AWS S3** | Negligible | **$0.01** | ₹1 |
| 9 | **Langfuse** | Free tier | **$0** | ₹0 |
| | | | | |
| | **TOTAL (Option B)** | | **~$11/mo** | **~₹920/mo** |

---

## 🆓 First 3-6 Months: Practically FREE

Most services offer generous free credits that will cover your usage entirely during the initial months:

| Service | Free Credit | How Long It Lasts (at 5 calls/day) |
|---------|------------|--------------------------------------|
| **Deepgram** | $200 free credit | ~5+ months of STT + TTS combined |
| **LiveKit** | Free tier (50 participants/mo) | Covers development & testing |
| **Gemini Flash** | Free tier (generous) | Likely covers 5 calls/day entirely |
| **Twilio** | $15.50 trial credit | ~1 month |
| **ElevenLabs** | 10,000 chars/month free | ~7 calls worth (not much) |

> **Bottom line: Your first 3-6 months can cost ₹0 (or close to it)** using free tier credits.

---

## 📊 Side-by-Side Comparison

```
┌─────────────────────────────────────────────────────────────┐
│              MONTHLY COST AT 5 CALLS/DAY                    │
│                                                             │
│  Option A (ElevenLabs)    ████████████████████████  ₹2,650  │
│  Option B (Deepgram TTS)  ██████                    ₹920    │
│                                                             │
│  Savings with Option B:  ₹1,730/month (65% cheaper!)       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 My Recommendation

**Start with Option B (Deepgram TTS) at ~₹920/month.**

Reasons:
1. **₹920/month is extremely affordable** for a production AI voice system
2. Deepgram TTS (Aura) quality is excellent — fast, natural-sounding, low latency
3. You save **₹1,730/month** compared to ElevenLabs
4. First few months are **completely free** using credits
5. You can always **upgrade to ElevenLabs later** for premium voice quality if needed

**Hybrid Option (Best of Both Worlds):**
- Use **ElevenLabs** for just the greeting message (first impression matters)
- Use **Deepgram TTS** for all other responses (80% of the conversation)
- Cost: ~₹1,100/month — premium greeting, affordable everything else

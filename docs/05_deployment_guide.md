# Deployment Guide — What You Actually Need (and What You Don't)

## The Honest Truth About Your Scale :

| Your Scale | What Companies Use | What YOU Need |
|---|---|---|
| 5 calls/day | ❌ Kubernetes is overkill | ✅ Single server + Docker |
| 50 calls/day | ❌ Still overkill | ✅ Single server + Docker |
| 500+ calls/day | 🟡 Maybe | ✅ 2-3 servers + load balancer |
| 5000+ calls/day | ✅ Yes, Kubernetes | Full orchestration |

> **Bottom line: You need Docker. You do NOT need Kubernetes.**
> Kubernetes is for companies handling thousands of concurrent users with dozens of microservices.
> Using it at 5 calls/day is like renting a Boeing 747 to go to the grocery store.

---

## What Each Technology Is (Simple Explanation)

### 🐳 Docker — YES, We Use This
**What it does:** Packages your entire app (code + dependencies + settings) into a single "container" that runs identically everywhere — your laptop, a cloud server, anywhere.

**Why we need it:**
- Your app has many dependencies (Python, Redis, PostgreSQL, etc.)
- Without Docker, you'd need to install everything manually on the server
- Docker = "it works on my machine" → "it works everywhere"

**What you'll do:**
```
# Build your app into a container
docker build -t voice-agent .

# Run it
docker-compose up
```

That's it. You already know these commands.

---

### 🐳 Docker Compose — YES, We Use This
**What it does:** Runs MULTIPLE Docker containers together. Our app needs several services running simultaneously.

**Our docker-compose.yml will run:**
```
┌─────────────────────────────────────────────────┐
│           docker-compose up                      │
│                                                  │
│  ┌──────────────┐  ┌──────────────┐             │
│  │  voice-agent  │  │   Redis      │             │
│  │  (our Python  │  │   (session   │             │
│  │   app)        │  │    memory)   │             │
│  └──────────────┘  └──────────────┘             │
│                                                  │
│  ┌──────────────┐  ┌──────────────┐             │
│  │  PostgreSQL   │  │   FastAPI    │             │
│  │  (database)   │  │   (dashboard │             │
│  │              │  │    + API)    │             │
│  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────┘
```

One command starts everything. One command stops everything.

---

### ☸️ Kubernetes — NO, We Don't Need This
**What it does:** Manages hundreds/thousands of Docker containers across many servers. Auto-scales, auto-heals, load balances.

**Why NOT for us:**
- We have 5 calls/day, not 5000
- Kubernetes requires significant DevOps expertise to manage
- It adds complexity without any benefit at our scale
- The cloud bill increases for the Kubernetes cluster itself

**When you'd upgrade to it:** If you grow to 500+ concurrent calls and need auto-scaling. We can migrate later — Docker makes this easy.

---

## Our Deployment Strategy (Simple & Production-Ready)

### Option A: Railway / Render (EASIEST — Recommended to Start)
**Cost: $5-20/month**

These platforms take your Docker container and deploy it automatically. Zero server management.

```
You push code to GitHub
        │
        ▼
Railway/Render detects the change
        │
        ▼
Automatically builds Docker image
        │
        ▼
Deploys your app
        │
        ▼
Gives you a public URL (https://your-app.railway.app)
        │
        ▼
Twilio SIP trunk points to this URL → calls work!
```

**Pros:** No server to manage, automatic HTTPS, auto-deploy on git push
**Cons:** Slight cost premium vs raw VPS

---

### Option B: Single VPS (DigitalOcean / AWS EC2 / Hetzner)
**Cost: $10-25/month**

You rent a single Linux server and run Docker Compose on it.

```
┌──────────────────────────────────────┐
│  DigitalOcean Droplet ($12/month)    │
│  Ubuntu 24.04, 2 CPU, 4GB RAM       │
│                                      │
│  ┌────────────────────────────────┐  │
│  │      docker-compose up        │  │
│  │                                │  │
│  │  voice-agent + redis +        │  │
│  │  postgresql + fastapi         │  │
│  └────────────────────────────────┘  │
│                                      │
│  Nginx (reverse proxy + HTTPS)       │
└──────────────────────────────────────┘
```

**Pros:** Full control, cheaper, can SSH in and debug
**Cons:** You manage the server (updates, security, backups)

---

### Option C: AWS (More Complex, More Control)
**Cost: $20-50/month**

Uses managed AWS services instead of running everything on one server.

```
┌─────────────────────────────────────────────┐
│  AWS Setup                                   │
│                                              │
│  ECS Fargate (runs your Docker container)    │
│  ElastiCache (managed Redis)                 │
│  RDS (managed PostgreSQL)                    │
│  S3 (audio storage — already in our plan)    │
│  CloudWatch (monitoring/logs)                │
└─────────────────────────────────────────────┘
```

**Pros:** Each service is managed by AWS (auto-backups, auto-updates)
**Cons:** More expensive, AWS learning curve, configs can be complex

---

## My Recommendation

```
┌─────────────────────────────────────────────────────────────┐
│                     DEPLOYMENT ROADMAP                       │
│                                                              │
│  Phase 1 (NOW):       Develop locally with Docker Compose    │
│                        Everything runs on your laptop         │
│                                                              │
│  Phase 2 (Launch):    Deploy to Railway or Render             │
│                        Push to GitHub → auto-deploys          │
│                        Cost: ~₹1,200/month ($15)             │
│                                                              │
│  Phase 3 (Growth):    Move to DigitalOcean VPS if needed     │
│                        More control, slightly cheaper         │
│                                                              │
│  Phase 4 (Scale):     Only if 500+ calls/day                 │
│                        Consider AWS ECS or Kubernetes         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## What We Will Build (Deployment Files)

```
voice_agent/
├── Dockerfile                 # Packages our Python app
├── docker-compose.yml         # Runs app + Redis + PostgreSQL locally
├── docker-compose.prod.yml    # Production config (different passwords, etc.)
├── .dockerignore              # Excludes .env, .venv, etc. from container
├── nginx/
│   └── nginx.conf             # Reverse proxy config (for VPS deployment)
└── .github/
    └── workflows/
        └── deploy.yml         # Auto-deploy on git push (CI/CD)
```

---

## Summary Table

| Technology | Do We Need It? | When? |
|---|---|---|
| **Docker** | ✅ YES | From Day 1 — packages our app |
| **Docker Compose** | ✅ YES | From Day 1 — runs all services together |
| **GitHub Actions (CI/CD)** | ✅ YES | From launch — auto-deploy on push |
| **Nginx** | 🟡 Maybe | Only if using a VPS (Option B) |
| **Kubernetes** | ❌ NO | Only if you hit 500+ calls/day (months/years away) |
| **Terraform** | ❌ NO | Only if managing complex AWS infrastructure |
| **Load Balancer** | ❌ NO | Only if running multiple server instances |

---

## Hardware Requirements (For Your Server)

At 5 calls/day, extremely modest:

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 2 GB | 4 GB |
| Storage | 20 GB | 40 GB (for audio recordings) |
| Network | Standard | Standard (LiveKit handles media) |

A **$12/month DigitalOcean droplet** or a **$5/month Railway starter** handles this easily.

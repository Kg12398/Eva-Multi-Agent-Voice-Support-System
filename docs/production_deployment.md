# 🚀 Production Deployment Guide: KG ElectroPower Voice Agent ("Gauri")

This document outlines the strategic and technical requirements for transitioning the **KG ElectroPower Voice Agent** from local development to a robust, scalable, and secure production environment.

---

## 🏗️ Domain Classification: DevOps vs. LLMOps vs. VoiceOps

Deploying Gauri involves three primary disciplines:

1.  **DevOps (Infrastructure & Automation):** Focuses on the "containerized" nature of the application. It handles Kubernetes clusters, PostgreSQL/Redis hosting, CI/CD pipelines, and general network security.
2.  **LLMOps (Large Language Model Operations):** Specifically tailored for Gauri’s AI components. This involves:
    *   **Prompt Management:** Versioning the system prompts in `app/utils/constants.py`.
    *   **Vector DB Management:** Ensuring ChromaDB is synced and optimized in production.
    *   **Evaluation:** Using tools like LangFuse to review conversation quality and token usage.
3.  **VoiceOps (Real-time Audio):** A specialized subset of DevOps focusing on low-latency WebRTC/SIP connections, audio jitter, and packet loss monitoring.

---

## 🛠️ Phase 1: Recommended Architecture (AWS Example)

For a high-availability production setup, the following stack is recommended:

| Layer | Service | Purpose |
| :--- | :--- | :--- |
| **Orchestration** | **Amazon EKS (Kubernetes)** | Scalable pod-based execution for `livekit_worker`. |
| **Database** | **Amazon RDS (PostgreSQL 16)** | Managed relational storage for tickets and call records. |
| **Cache & Session** | **Amazon ElastiCache (Redis)** | Persistent storage for `CallSession` states across workers. |
| **Vector Search** | **Managed Pinecone / Chroma** | Scalable semantic search for the troubleshooting KB. |
| **Media Server** | **LiveKit Cloud / Self-hosted** | Manages the SFU (Selective Forwarding Unit) for voice streams. |
| **Secrets** | **AWS Secrets Manager** | Secure storage for API keys (Groq, Deepgram, LiveKit). |

---

## 🔄 Phase 2: End-to-End Workflow

### 1. Local Development
- Develop and test using `test_gauri.py`.
- Ensure all environment variables are in `.env.example`.

### 2. Containerization (Docker)
Create a `Dockerfile` that pre-installs the SentenceTransformer models to avoid runtime downloads.

### 3. CI/CD Pipeline (GitHub Actions)
- **Trigger:** On push to `main` or creation of a `Release`.
- **Steps:**
    1.  **Test:** Run `pytest` and linter checks.
    2.  **Build:** Create a Docker image using the `requirements.txt`.
    3.  **Scan:** Use `Trivy` or `Snyk` to check for OS/Python vulnerabilities.
    4.  **Push:** Upload image to **Amazon ECR**.
    5.  **Deploy:** Update the Kubernetes Deployment to use the new image hash.

---

## 🔐 Phase 3: Key Security Best Practices

1.  **Network Isolation:** Deploy all database and cache instances in a **Private Subnet** within a VPC. Use **Security Groups** to white-list only the EKS cluster IP range.
2.  **IAM Roles for Service Accounts (IRSA):** Avoid passing hardcoded AWS credentials. Use EKS IAM roles to give pods permission to access S3 or Secrets Manager.
3.  **API Security:** 
    *   Use an **API Gateway** if exposing any REST endpoints (FastAPI).
    *   Protect the Groq/Deepgram keys using server-side injection only.
4.  **Data Protection:** Enable **AES-256 Encryption at Rest** for RDS and S3. Ensure TLS 1.3 for all data in transit.

---

## 📈 Phase 4: Monitoring, Logging, and Scaling

### Monitoring & Observability
- **Tooling:** Prometheus (metrics) + Grafana (dashboards) + Loki (logs).
- **Critical Metrics:**
    - **TTFT (Time To First Token):** Measures voice response latency.
    - **VAD Accuracy:** Track if Silero VAD is cutting off users too early.
    - **LLM Rate Limits:** Track 429 errors from Groq.

### Scaling Strategies
- **Horizontal Pod Autoscaling (HPA):** Scale workers based on the number of active LiveKit rooms.
- **Connection Pooling:** Use **SQLAlchemy pool_size** or **PgBouncer** to handle high concurrent DB connections.

---

## ⚠️ Phase 5: Common Mistakes to Avoid

1.  **Local Volume Dependence:** Never save session data to the pod's local disk; use Redis.
2.  **Ignoring Latency Regions:** Deploying the LLM worker in `us-east-1` for users in `ap-south-1` (India) adds ~300ms of lag. Match the region to the user base.
3.  **Missing Global Rate Limiter:** If 50 pods hit Groq at the same time, your token bucket will empty instantly. Use a distributed lock via Redis for rate control.
4.  **Model Loading at Runtime:** Downloading `all-MiniLM-L6-v2` when a pod starts adds 30+ seconds to boot time. **Bake it into the Docker image.**

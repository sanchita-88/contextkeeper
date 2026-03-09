![ContextKeeper Banner](https://img.shields.io/badge/ContextKeeper-Developer_Intelligence_Hub-4c1?style=for-the-badge&logo=amazonaws&logoColor=white)

### ContextKeeper: Developer Intelligence Hub 🚀

**Built for AI for Bharat Hackathon 2026 | Powered by AWS**

> Stop losing hours to context switching. ContextKeeper captures your full development context, indexes your codebase into a vector database, and gives you RAG-powered answers, diagrams, and focus protection so you can resume deep work in seconds.

---

### 🧩 1. Problem Statement — Losing Context is Costly

Modern developers constantly juggle:

- Multiple microservices and repositories
- Parallel features and bugfixes
- PR reviews, Slack pings, incidents, and meetings

Every interruption forces a **re-onboarding tax**: reconstructing what you were doing, which files were open, what was half-implemented, and why certain decisions were made. Research shows:

- **23 minutes** average to fully regain focus after an interruption  
- **Hundreds of hours per developer per year** lost to context recovery

Teams pay this cost silently across sprints, leading to:

- Slower delivery cycles
- More bugs introduced during “re-entry”
- Burnout from constant context reconstruction

**ContextKeeper** is designed to be the missing *memory layer* for developers.

---

### 💡 2. Solution Overview — ContextKeeper in One Line

**ContextKeeper is a Developer Intelligence Hub that:**

- **Captures** rich, AI-enriched snapshots of your work state (files, TODOs, commands, tags)
- **Indexes** your repositories into a **Qdrant** vector store using **AWS Bedrock Titan Embeddings V2**
- **Answers** natural-language questions over your code using **Groq Llama 3** via a FastAPI backend
- **Visualizes** flows and architectures with AI-generated **Mermaid.js diagrams**
- **Shields** your focus by classifying interruptions and generating professional auto-replies

The result: when you come back after minutes, hours, or days, you get an AI briefing that tells you **exactly** what you were doing and what to do next.

---

### 🌟 3. Key Features (from the codebase)

- **Context Snapshots / Checkpoints**
  - Frontend: `CheckpointPage` (`app/dashboard/checkpoint/page.tsx`)
  - Backend: `ContextSnapshot` / `SnapshotCreateRequest` models and `/snapshots` routes  
  - Captures:
    - Active file and open files (with cursor positions)
    - TODOs and terminal commands
    - Project path and tags
  - Backend enriches each snapshot with:
    - `ai_summary` — short narrative of what you were doing
    - `next_steps` — concrete next actions

- **Dashboard & Resume Flow**
  - `DashboardPage` lists snapshots, tags, and quick stats.
  - `ResumePage` (`/dashboard/resume/[id]`) fetches a snapshot and calls `/snapshots/{id}/resume` to generate an **AI re-orientation briefing** (“Welcome back! You were working on…”).

- **Codebase Q&A (RAG over Code)**
  - Frontend page: `app/dashboard/codebase/page.tsx`
  - Backend:
    - `/query` endpoint (in `main.py` and `rag_engine.py`)
    - Uses **Qdrant** via `vector_store.py` + **AWS Bedrock Titan Embeddings V2** for code chunk embeddings.
    - Builds graph context using `graph_engine.py`.
    - Calls Groq LLM (`ai_service.py` / `groq_service.py`) for natural language answers.
  - Returns:
    - Rich `answer`
    - Ranked `code_snippets` with file paths and line ranges
    - `relevant_files` list
    - Optional `mermaid_diagram`

- **Smart Diagrams**
  - Frontend page: `app/dashboard/diagram/page.tsx`
  - Backend endpoint: `/diagram`
  - Uses `ai_service.generate_mermaid_diagram` / `groq_service.generate_mermaid_diagram` with a strong sanitization pipeline to:
    - Generate **sequence**, **flowchart**, or **class** diagrams in Mermaid.js
    - Strip non-Mermaid text and enforce safe, renderable diagrams

- **Focus Shield — Interruption Triage**
  - Frontend page: `app/dashboard/interruptions/page.tsx`
  - Backend endpoints:
    - `/interruptions/classify` — classifies incoming messages
    - `/interruptions` — lists historical interruptions
  - `interruption_service.py` and `ai_service.classify_interruption` / `groq_service.classify_interruption`:
    - Priority buckets: `critical`, `important`, `deferrable`
    - Generates auto-reply text and suggested defer duration
    - Logs interruptions to SQLite for stats

- **Impact Analysis**
  - Backend endpoint: `/impact`
  - Uses `graph_engine.get_impact` to answer: *“What breaks if I change this function?”*  
  - Returns affected functions/files and a computed risk level.

- **Indexing & RAG Engine**
  - `/index` and `/index/status` (FastAPI) plus higher-level `rag_engine.index_project`
  - Handles:
    - Walking project directories
    - Chunking code via `code_analyzer.py`
    - Embedding via AWS Bedrock Titan
    - Storing vectors in Qdrant with payloads (path, lines, language)
    - Storing metadata in `IndexedProjectDB` (SQLite)

- **Landing Experience & Tech Stack Showcase**
  - Rich Next.js 14 landing page (`app/page.tsx`) with:
    - Hackathon tag: “AI for Bharat Hackathon 2026”
    - Animated 3D background (`ThreejsBackground`)
    - Highlight tiles for Qdrant, Llama 3 via Groq, NetworkX, Tree-sitter, etc.

---

### 🏗️ 4. High-Level Architecture (Text Diagram)

```text
Developer Browser (Next.js 14 / React)
        |
        |  HTTPS (fetch)
        v
Next.js Frontend (Vercel/Amplify-ready SPA + App Router)
        |
        |  REST API calls (CORS enabled for localhost + *.amplifyapp.com)
        v
AWS API Gateway (recommended edge entry)   <-- (Hackathon deployment layer)
        |
        |  Proxy to container / EC2
        v
FastAPI Backend (Python, async)
  - /snapshots, /query, /diagram, /interruptions, /impact, /index, /index/status
        |
        +--> Qdrant Vector DB (managed / self-hosted)
        |      - Stores Titan embeddings for code chunks
        |
        +--> AWS Bedrock (Titan Text Embeddings V2)
        |      - `bedrock-runtime` client in `bedrock_embeddings.py` & `vector_store.py`
        |
        +--> Groq LLM API (Llama 3)
        |      - `groq_service.py` / `ai_service.py`
        |
        +--> SQLite / Postgres (SQLAlchemy async)
               - Snapshots, indexed projects, interruption logs
```

---

### ☁️ 5. AWS Services Used (as wired in the code)

- **Amazon Bedrock — Titan Text Embeddings V2**
  - Files: `backend/bedrock_embeddings.py`, `backend/vector_store.py`
  - Used to embed code chunks and queries into **1024-dim vectors**.
  - Reason:
    - Fully managed, highly scalable embedding service
    - Strong fit for **RAG over code** with consistent vector size and performance.

- **Amazon EC2 (for backend compute)**
  - The FastAPI backend plus Qdrant can be containerized and deployed on EC2 (or ECS/EKS).
  - Reason:
    - Fine-grained control over Python runtime, Qdrant process, and GPU/CPU selection.
    - Easy to attach IAM roles for Bedrock access.

- **AWS Amplify (for frontend hosting)**
  - Live demo uses an Amplify URL: `https://main.d2vqjn3msa53j5.amplifyapp.com`.
  - Reason:
    - Zero-devops hosting for the Next.js 14 frontend.
    - Git-based CI/CD with preview environments for hackathon speed.

- **Amazon API Gateway (recommended in front of FastAPI)**
  - While the repo directly exposes FastAPI (`uvicorn.run` on `0.0.0.0:backend_port`), the hackathon deployment is designed to front this with API Gateway.
  - Reason:
    - Centralized auth, throttling, and observability.
    - Clean public URL for the Next.js frontend to call (`NEXT_PUBLIC_API_URL`).

> Note: The repo directly initializes Bedrock through `boto3.client("bedrock-runtime", region_name="us-east-1")`, making it ready for AWS deployment with standard credentials (IAM role, environment, or shared config).

---

### 🧰 6. Tech Stack Summary

| Layer           | Technology (from code)                                             |
|----------------|--------------------------------------------------------------------|
| **Frontend**   | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Framer Motion, React Three Fiber |
| **Backend**    | FastAPI (async), Pydantic v2, SQLAlchemy async, Uvicorn           |
| **Vector DB**  | Qdrant (`qdrant-client` AsyncQdrantClient)                        |
| **Embeddings** | Amazon Bedrock **Titan Text Embeddings V2** via `boto3`          |
| **LLM**        | Groq Llama 3 (`groq`, `langchain-groq`) for reasoning + generation |
| **RAG Engine** | Custom `rag_engine.py`, `vector_store.py`, `code_analyzer.py`, `graph_engine.py` |
| **Database**   | SQLite (dev) / Postgres-ready via SQLAlchemy                      |
| **Hosting**    | AWS Amplify (frontend), EC2/API Gateway (backend, recommended)    |

---

### 🔄 7. How It Works — End-to-End Flow

#### 7.1 Creating a Context Checkpoint

1. **User opens the Checkpoint UI** (`/dashboard/checkpoint`).
2. They fill in:
   - Project path, active file, open files, TODOs, recent commands, tags.
3. Frontend submits to **`POST /snapshots`**.
4. Backend:
   - Normalizes snapshot via `ContextSnapshot` model.
   - Enriches context with AI using Groq LLM:
     - `generate_context_summary(...)`
     - `generate_next_steps(...)`
   - Persists snapshot JSON into SQLite (`SnapshotDB`).
5. Dashboard (`/dashboard`) queries **`GET /snapshots`** and renders snapshot cards.

#### 7.2 Resuming Work

1. User clicks a snapshot card → navigates to `/dashboard/resume/[id]`.
2. Frontend calls **`GET /snapshots/{id}`** (and optionally `/snapshots/{id}/resume`).
3. Backend reconstructs `ContextSnapshot` and (for resume) calls `generate_resume_briefing`.
4. UI shows:
   - AI summary
   - AI next steps checklist
   - Open files, recent edits, and commands
   - Optional AI “Re-orient me” briefing for quick mental re-entry.

#### 7.3 Indexing a Codebase

1. User enters a local path or GitHub URL in **Codebase Intelligence** (`/dashboard/codebase`).
2. Frontend calls **`POST /index`** with `project_path`.
3. Backend background task:
   - If GitHub URL: clones into a temp dir.
   - Walks project files (`code_analyzer.scan_project` / `walk_project`).
   - Parses & chunks code (per file) and builds a **call graph** via `graph_engine.add_file`.
   - Uses **AWS Bedrock Titan** to:
     - Embed each chunk (`bedrock_embeddings.py` / `vector_store.embed_texts`).
     - Store vectors in **Qdrant** with payloads (file path, lines, language, project_path).
   - Stores index metadata in SQLite (`IndexedProjectDB`).
4. Frontend polls **`GET /index/status?project_path=...`** and shows progress.

#### 7.4 Asking Questions About the Code

1. User selects an indexed repo and types a question (e.g., *“How does authentication work?”*).
2. Frontend posts to **`POST /query`** with `{ question, project_path }`.
3. Backend:
   - Verifies index status in `_indexing_progress` / `IndexedProjectDB`.
   - Searches Qdrant using Titan embeddings for the query.
   - Builds `code_chunks` and `graph_context`.
   - Calls Groq LLM (`answer_codebase_question`) with the combined context.
   - Optionally calls `generate_mermaid_diagram` to produce a Mermaid diagram.
4. Frontend renders:
   - AI answer
   - Snippets with file/line ranges
   - Relevant file list
   - Rendered diagram using `DiagramViewer`.

#### 7.5 Generating Standalone Diagrams

1. User opens `/dashboard/diagram`, chooses a type (sequence / flowchart / class), and enters a query.
2. Frontend calls **`POST /diagram`** with `{ query, project_path, diagram_type }`.
3. Backend:
   - Optionally pulls vector context from Qdrant (`vector_store.search`).
   - Calls Groq LLM with code + query.
   - Runs the custom Mermaid sanitisation pipeline (`groq_service._sanitise_diagram`).
4. Frontend displays the diagram and allows downloading the `.mmd` source.

#### 7.6 Focus Shield — Interruption Classification

1. User pastes an incoming message into `/dashboard/interruptions`.
2. Frontend calls **`POST /interruptions/classify`** with `{ message, source, current_context }`.
3. Backend:
   - Routes through `interruption_service.triage` → `ai_service.classify_interruption`.
   - Groq LLM returns JSON with:
     - Priority, reason, auto-reply, defer duration, action_required.
   - Logs interruption to SQLite via `InterruptionLogDB`.
4. Frontend:
   - Shows a **Priority badge** (critical / important / deferrable).
   - Surfaces the AI-written auto-reply for quick copy-paste.
   - Renders an interruption log with daily stats.

---

### 🎥 8. Live Demo

- **Production Frontend** (hosted on AWS Amplify):  
  `https://main.d2vqjn3msa53j5.amplifyapp.com`

---

### 🧪 9. Setup & Installation (Local)

> Prerequisites: Node.js (LTS), Python 3.10+, Qdrant instance (local Docker or managed), AWS credentials with Bedrock access, Groq API key.

#### 9.1 Clone the repo

```bash
git clone <your-fork-or-repo-url>
cd contextkeeper-frontend
```

---

#### 9.2 Backend (FastAPI) — `backend/`

1. **Create and activate a virtualenv** (recommended):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Configure environment variables**:

- Copy the example file:

```bash
cp .env.example .env
```

- Fill in real values for:
  - `GROQ_API_KEY`
  - `GROQ_FAST_MODEL`
  - `GROQ_SMART_MODEL`
  - `QDRANT_URL`
  - `QDRANT_API_KEY`
  - `DATABASE_URL` (optional, defaults to SQLite if not changed)
  - `BACKEND_PORT` (defaults to 8000 in `config.py`)

4. **Run the backend**:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The OpenAPI docs will be available at `http://localhost:8000/docs`.

---

#### 9.3 Frontend (Next.js) — root

1. Install Node dependencies:

```bash
cd ..
npm install
```

2. Configure frontend environment:

- Create a `.env.local` file:

```bash
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

3. Run the dev server:

```bash
npm run dev
```

4. Open the app at `http://localhost:3000` and:
   - Create a checkpoint.
   - Index a local project path via **Codebase Intelligence**.
   - Classify interruptions via **Focus Shield**.

---

### 🔐 10. Environment Variables (from the repo)

#### Backend (`backend/.env` derived from `.env.example` & `config.py`)

- **AI / LLM**
  - `GROQ_API_KEY` — Groq API key for Llama 3.
  - `GROQ_FAST_MODEL` — fast model name (e.g. `llama3-8b-8192`).
  - `GROQ_SMART_MODEL` — reasoning model name (e.g. `llama3-70b-8192`).

- **Vector DB / RAG**
  - `QDRANT_URL` — Qdrant endpoint (e.g. `http://localhost:6333`).
  - `QDRANT_API_KEY` — Qdrant API key (blank for local dev).

- **Database**
  - `DATABASE_URL` — SQLAlchemy DB URL.
    - Example dev: `sqlite:///contextkeeper.db`
    - Example prod: `postgresql://user:password@host/contextkeeper`

- **Server**
  - `BACKEND_PORT` — FastAPI port (default: `8000`).

> AWS Bedrock credentials are read from standard AWS config (env vars / IAM role), not from a dedicated env var in this repo.

#### Frontend (`.env.local` / process env)

- `NEXT_PUBLIC_API_URL`
  - Used in `lib/config.ts` and several pages to point to the backend:
  - Defaults to `http://localhost:8000` if not set.

---

### 🔌 11. Key API Endpoints (FastAPI)

All routes are defined in `backend/main.py` and related services:

- **Health**
  - `GET /health` — basic health check.

- **Snapshots / Checkpoints**
  - `POST /snapshots` — create a new snapshot with AI summary & next steps.
  - `GET /snapshots` — list recent snapshots.
  - `GET /snapshots/{snapshot_id}` — get a single snapshot.
  - `DELETE /snapshots/{snapshot_id}` — delete a snapshot.
  - `GET /snapshots/{snapshot_id}/resume` — AI re-orientation briefing.

- **Indexing / RAG**
  - `POST /index` — start background indexing for `project_path`.
  - `GET /index/status?project_path=...` — get indexing status and progress.
  - `POST /query` — RAG-powered Q&A over an indexed project.

- **Diagrams**
  - `POST /diagram` — generate Mermaid.js diagram from natural language + code context.

- **Impact Analysis**
  - `GET /impact?function_name=...&project_path=...` — upstream impact analysis from the call graph.

- **Interruptions / Focus Shield**
  - `POST /interruptions/classify` — classify an interruption and generate auto-reply.
  - `GET /interruptions` — list logged interruptions.

---

### 👥 12. Team

- **Team**: `[Team Name / Member Names]`

> Replace this with your actual team details for the AI for Bharat Hackathon 2026 submission.

---

### 📄 13. License

This project is licensed under the **MIT License**.

You are free to use, modify, and distribute this project, subject to the terms in the `LICENSE` file (or MIT template).

---

### 🏁 Why This Matters for AI for Bharat

- **Developer Productivity for India at Scale**: Large engineering teams in India work across sprawling microservice architectures; context loss is a daily, compounding tax.
- **Practical RAG on Real Codebases**: This project shows a concrete, production-minded RAG stack using **AWS Bedrock + Qdrant + Groq**.
- **AWS-Native Friendly**: Uses official Bedrock runtime via `boto3`, works cleanly with Amplify, API Gateway, EC2, and managed vector options.

ContextKeeper turns every interruption into a **recoverable state**, making deep work sustainable and measurable for developers across Bharat. 🇮🇳


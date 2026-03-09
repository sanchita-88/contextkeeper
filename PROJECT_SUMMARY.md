# ContextKeeper — Project Summary
### AI for Bharat Hackathon 2026 | Hack2Skill x AWS

---

## 1. Problem Statement
Developers constantly lose context — what they were working on, why certain decisions were made, what files were open, what's left to do. This cognitive overhead kills productivity, especially when switching between tasks, returning after a break, or onboarding into a new codebase.

## 2. Our Solution
ContextKeeper is a **Developer Intelligence Hub** that adds a persistent “memory layer” on top of the development workflow. It combines **context snapshots**, **codebase RAG**, **architecture diagrams**, and **interruption triage** into a single system backed by AWS.

At its core, ContextKeeper:
- **Captures developer state**: open files, active file, recent edits, TODOs, terminal commands, project path, and tags are posted from the Next.js UI and stored as rich `ContextSnapshot` objects in the FastAPI backend.
- **Enriches that state with AI**: the backend calls Groq LLMs to generate an `ai_summary` and `next_steps` for every snapshot, so resuming work becomes as simple as reading a short briefing.
- **Indexes repositories for semantic search**: the backend walks a project (local path or cloned GitHub repo), chunks the code, embeds it with **Amazon Bedrock Titan Text Embeddings V2**, and stores vectors in **Qdrant**, keyed by project path.
- **Answers natural language questions about the code**: when a developer asks a question, ContextKeeper runs a full RAG pipeline (Bedrock + Qdrant + Groq) to return grounded, file-referenced answers and optional Mermaid diagrams.

The result is a vertically integrated tool that **saves**, **restores**, and **queries** developer context using a retrieval-augmented generation pipeline built entirely on AWS primitives.

## 3. Why AI Is Required
Explain why this problem cannot be solved without AI:
- Natural language querying of codebases requires semantic understanding, not keyword search
- Context generation from open files, todos, and terminal history requires LLM summarization
- Vector similarity search enables intelligent retrieval of relevant code chunks

## 4. AWS Services Used & Why
Cover each service used in the actual deployment:
- **Amazon Bedrock (Titan Text Embeddings V2)** — for generating 1024-dim semantic embeddings of code chunks; chosen for its high throughput (300K TPM), no cold start, and native AWS integration
- **Amazon EC2 (t3.small, us-east-1)** — hosts the FastAPI backend and Qdrant vector database; chosen for persistent storage of vector indices
- **AWS Amplify** — hosts the Next.js frontend with CI/CD from GitHub; chosen for zero-config HTTPS deployment
- **Amazon API Gateway (HTTP API)** — acts as HTTPS proxy between Amplify frontend and EC2 backend, solving mixed-content browser restrictions and enabling scalable routing

In the codebase, Titan is accessed via the official `boto3` **Bedrock Runtime** client (`bedrock_embeddings.py` and `vector_store.py`), making embedding calls first-class AWS operations. The FastAPI backend and Qdrant vector store are packaged as a Python service that can run on a small EC2 instance with sufficient disk for vector payloads. The Next.js 14 frontend is already deployed on an Amplify-hosted URL, and CORS configuration in FastAPI explicitly allows `*.amplifyapp.com`, reflecting the intended AWS-native deployment through API Gateway.

## 5. Architecture Overview
User → AWS Amplify (Next.js) → Amazon API Gateway → EC2 FastAPI Backend → [Qdrant Vector DB (on EC2) + Amazon Bedrock Titan Embeddings + Groq LLM]

**RAG pipeline, step by step (from code):**
1. **User submits a GitHub repo URL or local path** from the Codebase Intelligence page (`/dashboard/codebase`). The frontend sends the `project_path` to the FastAPI backend via the `/index` endpoint.
2. **Backend clones and chunks the codebase**. If the path is a GitHub URL, a background task clones it into a temp directory; then `code_analyzer` walks the project, parses each file, and produces language-aware code chunks plus a call graph via `graph_engine`.
3. **Each chunk is embedded via Amazon Bedrock Titan Embeddings V2**. The `vector_store` module calls the Bedrock Runtime client (`amazon.titan-embed-text-v2:0`) to obtain 1024-dim embeddings for each chunk, with retry and throttling logic tuned for production.
4. **Vectors are stored in Qdrant**. For each chunk, Qdrant receives a point containing the embedding and a payload (file path, start/end line, function name, language, and project_path) so lookups remain explainable and filterable.
5. **On user query, the query is embedded and top-k similar chunks are retrieved**. The `/query` endpoint embeds the user’s natural-language question via Titan, performs a filtered similarity search in Qdrant (by `project_path`), and retrieves the best-matching code chunks.
6. **Retrieved chunks + query are sent to Groq LLM for answer generation**. The backend composes a prompt containing the question, top code chunks, and graph context, then calls Groq’s Llama 3 models. The response is post-processed into:
   - A natural-language answer
   - A list of relevant files and structured code snippets
   - An optional Mermaid diagram generated by a dedicated diagram pipeline.

## 6. What Value the AI Layer Adds
- **Semantic code understanding across any repo**: Developers can ask free-form questions like “How does authentication work?” or “What happens when a payment fails?” and receive **grounded answers** referencing specific files and line ranges. This goes beyond grep or static indexing by using Titan embeddings + Groq reasoning over RAG context.
- **Checkpoint intelligence, not just storage**: The Checkpoint feature doesn’t just persist raw state; it calls Groq LLMs to turn open files, TODOs, and edit history into a concise `ai_summary` and an ordered list of `next_steps`. This dramatically reduces “cold start” time when resuming a session.
- **Diagram synthesis from real code**: The Diagrams feature uses the same code context and a specialised prompt + sanitisation pipeline (`groq_service.py`) to emit valid Mermaid sequence/flow/class diagrams. This lets developers visualize flows and architectures without manually drawing anything.
- **Focus Shield for interruption triage**: Incoming messages (Slack, PR requests, incidents, meetings) are passed through an LLM classifier that outputs a structured priority, rationale, defer duration, and a ready-to-send auto-reply. This AI layer converts noisy interrupts into actionable decisions, enabling data-driven focus time.

## 7. AWS-Native Patterns Used
- **Managed embedding service (Bedrock) instead of self-hosted models — reduces ops overhead**  
  ContextKeeper delegates all embedding work to **Amazon Bedrock Titan Text Embeddings V2**, eliminating the need to provision GPUs, manage model artifacts, or handle custom scaling. The backend code is simple `boto3` calls with automatic retries.

- **Amplify for frontend — serverless hosting with auto-scaling**  
  The Next.js 14 App Router UI is deployed on AWS Amplify (as evidenced by the `*.amplifyapp.com` demo URL and CORS configuration). Amplify handles SSL termination, build pipeline, and multi-environment support while the app itself remains a static/SSR React bundle.

- **API Gateway — decouples frontend from backend, enables future Lambda migration**  
  While the current backend runs as a FastAPI application on EC2, the design routes all browser traffic through **Amazon API Gateway (HTTP API)**. This keeps the public API surface independent of the compute implementation, making it straightforward to migrate selected endpoints to Lambda or add rate limiting and auth.

- **EC2 with persistent storage — suitable for stateful vector DB**  
  Qdrant and the FastAPI service are co-located on an EC2 instance, which provides local disk for vector indices and SQLite/Postgres data. This pattern keeps the vector store close to the embedding and query logic, minimizing latency while still leveraging AWS primitives for networking, IAM, and monitoring.

## 8. Live Demo
https://main.d2vqjn3msa53j5.amplifyapp.com

## 9. Tech Stack Summary
| Layer | Technology |
|-------|-----------|
| Frontend | Next.js, Tailwind CSS, AWS Amplify |
| Backend | FastAPI, Python, Amazon EC2 |
| Embeddings | Amazon Bedrock — Titan Text Embeddings V2 |
| Vector DB | Qdrant |
| LLM | Groq |
| API Layer | Amazon API Gateway |
| CI/CD | GitHub + AWS Amplify |

## 10. Team
[AntiGravity] | [Deepak Sethi, Sanchita Sabat, Nipun Taneja, Aadeep Aggarwal]

---


# ContextKeeper — Developer Intelligence Hub
# AI for Bharat Hackathon 2026

<div align="center">
  <h3>Stop losing hours to context switching.</h3>
  <p>Save your exact work state · Query your codebase with AI · Resume with one click</p>
</div>

---

## 🎯 What is ContextKeeper?

ContextKeeper is a full-stack **AI-powered developer productivity platform** that solves the $450 billion context-switching crisis. It acts as a **persistent memory layer** for your development work:

- **🧠 Context Snapshots** — Save your exact work state (open files, cursors, TODOs) and restore it with an AI-generated re-orientation briefing
- **🔍 Codebase Q&A** — Ask "How does auth work?" and get code snippets + architecture diagrams
- **🗺️ Smart Diagrams** — Auto-generate Mermaid.js sequence, flowchart, and class diagrams
- **🛡️ Focus Shield** — AI classifies interruptions by urgency and generates professional defer replies

---

## 🚀 Quick Start

### Frontend (Next.js)

```bash
cd contextkeeper-frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Backend (FastAPI)

```bash
cd contextkeeper-frontend/backend
cp .env.example .env
# Fill in your API keys
pip install -r requirements.txt
python main.py
```

API docs at [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14 (App Router) |
| **Styling** | Tailwind CSS — strict black & white theme |
| **LLM** | Groq API (`llama-3.3-70b-versatile`) |
| **Vector DB** | Qdrant Cloud (semantic code search) |
| **Embeddings** | `sentence-transformers` — `all-MiniLM-L6-v2` |
| **Backend** | FastAPI + SQLite (SQLAlchemy async) |
| **Code Graph** | NetworkX DiGraph (dependency mapping) |
| **Code Parsing** | Tree-sitter |
| **Diagrams** | Mermaid.js |

---

## 📁 Project Structure

```
contextkeeper-frontend/
├── app/
│   ├── page.tsx                    # Landing page
│   ├── layout.tsx                  # Root layout
│   └── dashboard/
│       ├── page.tsx                # Main dashboard
│       ├── checkpoint/page.tsx     # Save work state
│       ├── codebase/page.tsx       # Q&A interface
│       ├── diagram/page.tsx        # Diagram generator
│       ├── interruptions/page.tsx  # Focus Shield
│       └── resume/[id]/page.tsx    # One-click resume
├── components/
│   ├── Sidebar.tsx                 # Navigation sidebar
│   ├── SnapshotCard.tsx            # Context snapshot card
│   ├── DiagramViewer.tsx           # Mermaid.js renderer
│   └── PriorityBadge.tsx           # Interruption badge
└── backend/
    ├── main.py                     # FastAPI app + all routes
    ├── config.py                   # Pydantic settings
    ├── models.py                   # Request/response models
    ├── database.py                 # SQLite async ORM
    ├── ai_service.py               # Groq LLM calls
    ├── vector_store.py             # Qdrant embeddings
    ├── code_analyzer.py            # Tree-sitter parsing
    ├── graph_engine.py             # NetworkX dependency graph
    └── requirements.txt
```

---

## 🔑 Environment Variables

**Backend** (`backend/.env`):
```
GROQ_API_KEY=your_groq_api_key_here
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key_here
```

Get your keys:
- **Groq**: [console.groq.com](https://console.groq.com)
- **Qdrant**: [cloud.qdrant.io](https://cloud.qdrant.io)

---

## 🏗️ Core API Routes

| Method | Route | Description |
|---|---|---|
| `POST` | `/snapshots` | Create checkpoint with AI summary |
| `GET` | `/snapshots` | List all snapshots |
| `GET` | `/snapshots/{id}/resume` | Get snapshot + AI briefing |
| `POST` | `/index` | Ingest & index a codebase |
| `GET` | `/index/status` | Indexing progress |
| `POST` | `/query` | RAG-powered Q&A |
| `POST` | `/diagram` | Generate Mermaid diagram |
| `POST` | `/interruptions/classify` | Classify & auto-reply |
| `GET` | `/impact` | Impact analysis for a function |

---

## 🎨 Design System

- **Background**: Pure black `#000000`
- **Surface**: `#050505` / `#0a0a0a`
- **Text**: White primary, `zinc-400` secondary, `zinc-600` muted
- **Borders**: `#1a1a1a` default, `#333` hover
- **Fonts**: Inter (UI) + JetBrains Mono (code)
- **Philosophy**: Zero shadows, clean borders, typography-first

---

Built with ❤️ for **AI for Bharat Hackathon 2026**

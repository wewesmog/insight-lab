# Insight Lab

**Beyond positive/negative sentiment** — a minimal end-to-end demo for the [CVM-AI](https://github.com) YouTube channel.

Upload customer verbatims (CSV) → run a **LangGraph** pipeline → see **themes, churn risk, NPS class, issues, and delights** on a shadcn dashboard.

No API key required for the default demo (rule-based extraction). Set `OPENAI_API_KEY` to switch the graph to LLM extraction.

---

## What you get

| Layer | Tech | Role |
|-------|------|------|
| **Frontend** | Next.js + shadcn | Upload CSV, trigger analysis, view rollups |
| **API** | FastAPI | `POST /datasets/upload`, `POST /datasets/{id}/analyze` |
| **Pipeline** | LangGraph | `prepare → analyze_one (loop) → rollup_batch` |
| **Storage** | SQLite | Datasets + per-verbatim JSON analysis |

This repo is a **simplified cousin of [Echo](https://github.com)** — same ideas (structured extract → deterministic rollups), stripped down for teaching.

---

## Quick start

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional: add OPENAI_API_KEY

uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # optional; defaults to http://localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 3. Try it

1. Click **Kora Bank sample** or **Competitor switch sample** (bundled CSVs in `sample-data/`)
2. Click **Run analysis**
3. Explore theme counts, churn samples, and per-verbatim insight cards

### CLI (no UI)

```bash
cd backend
python scripts/run_analysis.py
```

---

## Data flow

```mermaid
flowchart LR
    subgraph Frontend
        UI[Next.js + shadcn]
    end

    subgraph API
        UP[POST /datasets/upload]
        AN[POST /datasets/{id}/analyze]
        IN[GET /datasets/{id}/insights]
    end

    subgraph Storage
        DB[(SQLite)]
    end

    subgraph Pipeline
        G[LangGraph]
    end

    CSV[CSV file] --> UI
    UI --> UP --> DB
    UI --> AN --> G
    G --> DB
    UI --> IN --> DB
```

**Key idea:** the LLM (or rules engine) only produces **per-verbatim records**. KPI cards and theme charts come from **deterministic rollups** in code — the model does not invent dashboard numbers.

See [docs/LANGGRAPH.md](docs/LANGGRAPH.md) for the graph tree and node-by-node walkthrough.

---

## CSV format

Minimum: one text column. Auto-detected names:

| Purpose | Accepted column names |
|---------|----------------------|
| Text | `verbatim`, `text`, `feedback`, `comment`, `message`, `review` |
| Rating | `star_rating`, `rating`, `stars`, `score` |
| Time | `timestamp`, `occurred_at`, `created_at`, `date` |
| ID | `id`, `verbatim_id`, `external_id` |

Examples: `sample-data/kora_bank_verbatims.csv`, `sample-data/competitor_switch_verbatims.csv`

---

## Project layout

```
insight-lab/
├── sample-data/           # Bundled demo CSV
├── backend/
│   ├── app/
│   │   ├── graphs/verbatim_insights/   # LangGraph (start here for videos)
│   │   ├── pipeline/                     # run.py, rules.py, rollup.py
│   │   ├── prompts/                      # LLM prompts (optional path)
│   │   ├── main.py                       # FastAPI routes
│   │   └── store.py                      # SQLite + CSV parse
│   └── scripts/run_analysis.py           # CLI demo
├── frontend/              # shadcn UI wired to API
└── docs/
    ├── LANGGRAPH.md       # Graph tree + node reference
    └── ARCHITECTURE.md    # System design
```

---

## Docs

- **[Video guide](docs/VIDEO_GUIDE.md)** — episode order, dual-screen setup, presentation PNGs, demo script
- **[LangGraph pipeline](docs/LANGGRAPH.md)** — graph diagram, state, routing, where to extend
- **[Architecture](docs/ARCHITECTURE.md)** — layers, API contract, comparison to Echo
- **[Diagram exports](docs/diagrams/README.md)** — PNG filenames for filming

---

## Optional: enable LLM

```bash
# backend/.env
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

Restart the API. The graph picks `engine=llm` automatically; `analyze_one` calls OpenAI instead of the rules module.

---

## License

MIT — use freely for learning, demos, and your own forks.
# insight-lab
# insight-lab

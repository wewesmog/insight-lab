# How Insight Lab works

Short guide for anyone reading the code. For YouTube presenter scripts, use the local `docs/` folder (gitignored).

---

## Big idea

1. Upload a CSV of customer comments (verbatims).
2. A **background job** runs a **LangGraph** pipeline.
3. The LLM fills **one structured record per row** (sentiment, themes, churn, …).
4. **Python** counts those records into KPIs (charts, inferred NPS).
5. Optional **enrich** + **executive summary** LLM calls use the rollup (and extra CSV columns).

The model does **not** invent dashboard percentages — code does.

---

## Request path

```
UI upload
  → POST /analyses/upload
  → store: parse CSV, create dataset + analysis (queued)
  → jobs.enqueue_analysis (thread)
  → run_insights_graph
  → save analysis_json + rollup when finished
UI polls GET /analyses/{id} until ready
```

Dev-only: `POST /test/langgraph` runs the same graph **without** creating a job.

---

## LangGraph (current)

```
prepare
  → analyze_one  ←──┐  (while pending_ids left)
  → rollup_batch ───┘
  → enrich_batch → summarize_batch   (if extras)
  → summarize_batch                  (if analyzed, no extras)
  → END                              (if all skipped)
```

| Step | File | Role |
|------|------|------|
| Graph wiring | `backend/app/graphs/verbatim_insights/graph.py` | Edges + routers |
| Nodes | `.../nodes.py` | Business logic per step |
| State | `.../state.py` | `records` append via `operator.add` |
| Skip junk | `backend/app/pipeline/skip.py` | Before LLM (incl. one-word) |
| KPIs | `backend/app/pipeline/rollup.py` | Counters / inferred NPS |
| Deep dive | `backend/app/pipeline/enrich.py` | Extras → segments → LLM |
| Board text | `backend/app/pipeline/summary.py` | Executive commentary |
| LLM | `backend/app/shared_services/llm.py` | Ollama / OpenAI / Gemini |

**Early exit:** all rows skipped → `END` (no enrich/summary).  
**Enrich:** only if any verbatim has `extras`; otherwise rollup → summarize.

---

## CSV rules

| Kept as first-class | Everything else |
|---------------------|-----------------|
| Text column (required) | → `extras` (channel, rating, nps, …) |
| Optional id / timestamp | |

There are **no** special survey fields on the models anymore.

---

## Persistence

| When | What |
|------|------|
| During loop | `processed_rows` progress only |
| After graph finishes | Each row’s `analysis_json` + analysis rollup / status |

Crash mid-run ⇒ no per-row analyses saved.

---

## Frontend

| Piece | Role |
|-------|------|
| `app-shell` | Sidebar list + upload; `{children}` = home or report |
| `analyses-list` | Paginated jobs, delete confirm |
| `analysis-report` | Management briefing (PDF / CSV export) |
| `lib/api.ts` | Thin fetch wrappers |

---

## Configure LLM

```bash
# backend/.env
LLM_PROVIDER=ollama          # or openai | gemini
OLLAMA_MODEL=llama3.2        # example
# OPENAI_API_KEY=...
# GOOGLE_API_KEY=...
```

`engine` on records / run response is the **resolved model name**.

---

## Where to look next

| Goal | Start here |
|------|------------|
| Add a graph node | `graph.py` + `nodes.py` |
| Change skip rules | `pipeline/skip.py` |
| Change extract fields | `prompts/extract.py` + `models.py` |
| Change KPIs | `pipeline/rollup.py` |
| Change report UI | `frontend/components/analysis-report.tsx` |

<h1 align="center">Tally</h1>

<p align="center"><em>Snap a receipt — Tally does the rest.</em></p>

A production-grade, agentic AI finance backend. **Tally** turns **photos of receipts**
into categorized, searchable expenses using a multi-agent pipeline — and lets you
**chat with your spending** in plain English. Built to showcase modern AI engineering
on top of a real, multi-tenant backend: agentic workflows with human-in-the-loop,
RAG / text-to-SQL, vector search, an MCP server, evals, and observability.

> Started life as a small LangGraph demo; rebuilt into a full backend with auth,
> async workers, Docker, and CI.

---

## ✨ What it does

| Capability | How |
|---|---|
| 📸 **Receipt → structured expense** | A LangGraph agent encodes the image, a **vision LLM** extracts fields, an LLM **categorizes**, and it's persisted to Postgres. |
| 🧑‍⚖️ **Human-in-the-loop over HTTP** | Low-confidence extractions **pause** the graph via `interrupt()` + a Postgres **checkpointer**; you review/correct/retry through REST and the graph **resumes**. |
| 🎯 **Confidence-gated automation** | High-confidence receipts auto-save; everything else routes to review. Multi-model **fallback** (OpenAI ↔ Anthropic). |
| 🔎 **Semantic search + dedup** | Expense embeddings in **pgvector** power "find similar" and **duplicate detection** (flagged into the review step). |
| 💬 **Chat with your expenses** | A **text-to-SQL ReAct agent** answers questions ("how much on Food last month?") with streamed (SSE) responses and conversation memory. |
| 📈 **Anomaly insights** | Statistical detectors (category spikes, duplicate charges) + an LLM narrator; available on-demand and as a monthly cron. |
| 🔌 **MCP server** | Exposes expense tools to **Claude Desktop** and other MCP clients. |
| 📊 **Evals + observability** | LangSmith dataset + field-accuracy evaluators; structured logs with PII redaction; health/readiness probes. |

---

## 🏗️ Architecture

```
                 ┌────────────── FastAPI (multi-tenant, JWT) ──────────────┐
   image ─▶ POST /receipts ─▶ enqueue (ARQ/Redis) ─▶ Worker                │
                 │                                      │                    │
                 │                          ┌───────────▼─────────────┐      │
                 │                          │   LangGraph receipt agent │      │
                 │   GET /jobs/{id}         │  encode→extract→categorize│      │
                 │   POST /jobs/{id}/resume │  →dup-check→confidence    │      │
                 │                          │   ├─ auto ─▶ persist       │      │
                 │                          │   └─ low  ─▶ interrupt() ──┼─ Postgres
                 │                          └───────────────────────────┘   checkpointer
   POST /chat ──▶ text-to-SQL ReAct agent ─▶ guarded read-only SQL ─▶ my_expenses view
   POST /search/semantic ─▶ embeddings ─▶ pgvector (<=>)
   GET  /insights/anomalies ─▶ statistical detectors + LLM narrator
                 └──────────────────────────────────────────────────────────┘
        Postgres (app data + pgvector + LangGraph checkpoints)   •   Redis (queue)
```

**Layering:** routers → services → repositories (raw SQL) → psycopg2 pool.
Tenancy is enforced in the repository layer (every query is scoped to `user_id`).
The LangGraph checkpointer uses a dedicated **psycopg3** pool against the same DB.

```
src/
├── main.py                # FastAPI app + lifespan (pools)
├── worker.py              # ARQ background worker + monthly cron
├── core/                  # config, logging (structlog), security (JWT/bcrypt), exceptions
├── db/                    # pool, session, checkpoint_pool, readonly, migrate, repositories/
├── services/              # auth, expense, receipt, job, embedding, chat, insights
├── agents/
│   ├── models.py          # model registry + multi-model fallback
│   ├── receipt_graph/     # the HITL extraction graph (nodes + state)
│   ├── sql_agent/         # text-to-SQL agent + SQL safety guard
│   └── insights_agent/    # anomaly detectors + LLM narrator
├── api/routers/           # auth, expenses, categories, payment_methods, receipts,
│                          #   graph, chat, search, insights, health
├── mcp/server.py          # MCP server (stdio)
└── evals/                 # labeled dataset + evaluators + runner
migrations/                # numbered SQL (yoyo): schema → users → jobs → pgvector → views → grants
```

---

## 🧰 Tech stack

**Python 3.12 · FastAPI · LangGraph 0.2 · LangChain 0.3 · PostgreSQL + pgvector ·
Redis + ARQ · psycopg2 (app) + psycopg3 (checkpointer) · Pydantic v2 · JWT/bcrypt ·
sqlglot · structlog · LangSmith · MCP · Docker · GitHub Actions.**

Models: OpenAI `gpt-4o` (vision/chat) + `text-embedding-3-small`, with Anthropic
`claude-3-7-sonnet` / `claude-3-5-haiku` as fallbacks (all configurable in `.env`).

---

## 🚀 Quickstart (Docker)

```bash
cp env.example .env          # then add OPENAI_API_KEY / ANTHROPIC_API_KEY
docker compose up --build
```

This starts Postgres (+pgvector), Redis, the API, and the worker; migrations + seed
data run automatically. Open **http://localhost:8000/docs**.

### Try it

```bash
# Register + log in
curl -X POST localhost:8000/auth/register -H 'content-type: application/json' \
  -d '{"email":"me@example.com","password":"supersecret123"}'
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -d 'username=me@example.com&password=supersecret123' | jq -r .access_token)

# Upload a receipt for async processing
curl -X POST localhost:8000/receipts -H "authorization: Bearer $TOKEN" \
  -F file=@data/walmart-bon.jpeg
# -> {"job_id": "...", "status": "pending"}

# Poll the job; if it needs review, resume it
curl localhost:8000/jobs/<job_id> -H "authorization: Bearer $TOKEN"
curl -X POST localhost:8000/jobs/<job_id>/resume -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' -d '{"decision":"accept"}'

# Chat with your expenses
curl -X POST localhost:8000/chat -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' -d '{"message":"How much did I spend on Food?"}'

# Semantic search + anomalies
curl -X POST localhost:8000/search/semantic -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' -d '{"query":"groceries"}'
curl localhost:8000/insights/anomalies -H "authorization: Bearer $TOKEN"
```

---

## 🧪 Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install .[dev]

# Point at a local Postgres (with pgvector) + Redis, then:
python -m src.db.migrate          # apply migrations + seed reference data
uvicorn src.main:app --reload     # API on :8000
arq src.worker.WorkerSettings     # background worker

pytest -q                         # unit + integration (integration auto-skips without a DB)
ruff check src tests              # lint
python -m src.evals.run_eval      # extraction eval (needs model keys)
```

---

## 🔒 Security highlights

- **Multi-tenant isolation** enforced at the repository layer — every query is
  scoped to `user_id`; covered by isolation tests.
- **Text-to-SQL safety**: an LLM never runs raw SQL. Queries pass a **sqlglot guard**
  (single read-only `SELECT`, allow-listed views only, mandatory `LIMIT`, blocked
  functions), then execute in a **read-only transaction** as a dedicated role against
  a **per-user view** scoped by a session GUC. Adversarial cases are tested.
- **Guardrails**: confidence-gated auto-accept, structured-output validation, and
  **PII redaction** in logs.

---

## 🔌 MCP (Claude Desktop)

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tally": {
      "command": "python",
      "args": ["-m", "src.mcp.server"],
      "env": { "PGHOST": "localhost", "MCP_USER_ID": "1", "OPENAI_API_KEY": "..." }
    }
  }
}
```

Tools: `list_expenses`, `add_expense`, `search_expenses_semantic`,
`get_spend_summary`, `detect_anomalies`, `query_expenses_nl`.

---

## 📋 Configuration

All settings live in `.env` (see `env.example`): database, Redis, JWT, model names +
fallbacks, the **auto-accept confidence threshold**, the **duplicate-distance
threshold**, LangSmith tracing, and the MCP user. Loaded once via pydantic-settings.

## License

See [LICENCE.txt](LICENCE.txt).

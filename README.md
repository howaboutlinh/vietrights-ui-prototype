# VietRights

Vietnamese-first workplace-rights assistant for migrant workers in Australia. The existing Flask intake UI is backed by a production-oriented retrieval-augmented generation (RAG) pipeline using Gemini, Flask-SQLAlchemy, Supabase Postgres, psycopg 3, and pgvector.

## Architecture

Offline ingestion (manual/admin only):

`4 approved source roots → bounded same-domain HTML/PDF crawler → cleaned sections → overlapping chunks → Gemini RETRIEVAL_DOCUMENT embeddings → SQLAlchemy transaction → Supabase pgvector`

Online `/analyze` request:

`Vietnamese scenario → concise English search rewrite → Gemini RETRIEVAL_QUERY embedding → cosine search → deduplicated evidence → grounded Gemini answer → Vietnamese UI with numbered sources`

The web process never scrapes or embeds source documents during startup or a normal request.

## Supabase setup

1. Create a free project at [Supabase](https://supabase.com/dashboard).
2. In **SQL Editor**, run [`supabase/migrations/001_vector_knowledge_base.sql`](supabase/migrations/001_vector_knowledge_base.sql). This enables pgvector, creates `knowledge_chunks`, RLS restrictions, an HNSW cosine index, and `match_knowledge_chunks`.
3. Find the project URL under **Project Settings → API**.
4. Open **Connect** at the top of the project page, choose **Session Pooler**, and copy its PostgreSQL connection string.
5. URL-encode special characters in the database password and set the SQLAlchemy driver scheme to `postgresql+psycopg://` (the application also safely normalizes `postgresql://` and `postgres://`). Keep `sslmode=require` in the URL or use the configured SSL connection option.

The application reads database credentials exclusively from `DATABASE_URL`. It does not use Supabase REST, Auth, or Storage, so `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are not required.

The SQL vector dimension is 768 and must match `EMBEDDING_DIMENSION=768`. Changing it requires a migration and re-embedding every document.

## Local configuration

```bash
cp .env.example .env
```

Required for web retrieval:

```text
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.6-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
DATABASE_URL=postgresql+psycopg://postgres.PROJECT:URL_ENCODED_PASSWORD@SESSION_POOLER_HOST:5432/postgres?sslmode=require
RAG_MATCH_COUNT=6
RAG_MATCH_THRESHOLD=0.60
EMBEDDING_DIMENSION=768
```

Ingestion additionally requires exactly four distinct approved HTTP(S) roots:

```text
KNOWLEDGE_SOURCE_1=
KNOWLEDGE_SOURCE_2=
KNOWLEDGE_SOURCE_3=
KNOWLEDGE_SOURCE_4=
```

Optional crawler controls are `HTTP_REQUEST_TIMEOUT_SECONDS=30`, `CRAWL_MAX_DEPTH=2`, and `CRAWL_MAX_PAGES=40`. Source URLs and all credentials remain environment variables; `.env` is ignored by Git.

## Install and run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Production start command:

```bash
gunicorn app:app
```

## Ingest knowledge

First validate extraction and chunking without API calls or database writes:

```bash
python scripts/ingest_knowledge.py --dry-run
python scripts/ingest_knowledge.py --source 1 --dry-run
```

Run real ingestion only after the migration and secrets are configured:

```bash
python scripts/ingest_knowledge.py
python scripts/ingest_knowledge.py --source 1
```

Each chunk has a SHA-256 hash derived from normalized content plus source URL. Re-running ingestion skips unchanged hashes and does not duplicate them. The command reports processed URLs/PDFs, created/skipped/updated chunks, and failures. Review website terms and crawling policies before ingestion, and use only content you are authorized to process.

## Agentic knowledge retrieval

`POST /analyze` sends the complete structured intake to a bounded Gemini research agent. The agent can call four read-only tools: semantic knowledge search, topic-focused search, adjacent-chunk lookup, and source-section lookup. English search queries are encouraged because the indexed official material is English; the original Vietnamese intake remains available to both retrieval and final response generation.

The server enforces a maximum of 8 tool calls across at most 3 planning rounds, at most 6 results per call, a 70-second research budget, pgvector similarity thresholds, and an allowlist that prevents section lookup for URLs not first returned by search. The model never receives database credentials, embeddings, or raw SQL access. Source metadata is attached by the server, and unsupported citation numbers cause the response to be rejected.

Successful responses are JSON with `content_format: "markdown"`, structured `summary`, `issues`, `evidence`, `next_steps`, `clarification_questions`, `risk_level`, and server-controlled `sources`. The frontend renders a safe Markdown subset using DOM nodes; it never injects model output as raw HTML.

## Test

```bash
pytest -q
```

Tests mock Gemini, HTTP/PDF behavior, and Supabase, so they do not consume API credits.

## Render deployment

Gemini research, embedding and answer calls retry transient HTTP 408/429/500/502/503/504 and transport failures up to six total attempts per call. Delays use exponential backoff (2, 4, 8, 16, 30 seconds plus jitter), honoring a longer provider retry delay. Authentication and invalid-request errors fail immediately. A shared 180-second AI request deadline bounds retries; a 70-second research budget still applies. Retries cannot restore exhausted quota.

The checked-in `gunicorn.conf.py` is loaded by `gunicorn app:app` and configures one worker, four threads, and a 210-second worker timeout. The browser waits up to 200 seconds. No Render command edit is needed to load these defaults. Error codes are translated to the selected UI language.

Create a Python Web Service and configure:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Environment: every web retrieval variable listed above
- Health URL: `/`

Add secrets in **Render Dashboard → Service → Environment**. Use the Supabase **Session Pooler** URL for `DATABASE_URL`; direct IPv6 database URLs are less suitable where the host lacks IPv6. Do not commit credentials. Deploy starts only the Flask web application. Run ingestion separately as a manual/admin job from a trusted environment with the four source variables set. A restart or redeploy must not scrape and re-embed the sources.

SQLAlchemy is configured for Render with `pool_pre_ping=True`, `pool_recycle=300`, a pool size of 3, max overflow of 2, and a 30-second pool timeout. The application never calls `db.create_all()`; the versioned SQL migration remains the production schema source.

To refresh content safely, run the ingestion command again. Unchanged chunks are skipped. Inspect failures and retrieval quality before relying on newly indexed content.

## Security and answer behavior

- `DATABASE_URL` is a backend-only secret and must never appear in HTML, frontend JavaScript, logs, or responses.
- RLS continues to deny access to Supabase public client roles. The Flask backend connects directly through the protected Session Pooler database user.
- Source and model text is rendered with DOM `textContent`, not unsanitized `innerHTML`.
- If no evidence passes the configured threshold, VietRights returns a cautious no-evidence message instead of generating a legal answer.
- VietRights provides general information, not professional legal advice.

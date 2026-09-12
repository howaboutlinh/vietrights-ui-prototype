# VietRights

Vietnamese-first workplace-rights assistant for migrant workers in Australia. The existing Flask intake UI is backed by a production-oriented retrieval-augmented generation (RAG) pipeline using Gemini, Supabase Postgres, and pgvector.

## Architecture

Offline ingestion (manual/admin only):

`4 approved source roots → bounded same-domain HTML/PDF crawler → cleaned sections → overlapping chunks → Gemini RETRIEVAL_DOCUMENT embeddings → Supabase pgvector`

Online `/analyze` request:

`Vietnamese scenario → concise English search rewrite → Gemini RETRIEVAL_QUERY embedding → cosine search → deduplicated evidence → grounded Gemini answer → Vietnamese UI with numbered sources`

The web process never scrapes or embeds source documents during startup or a normal request.

## Supabase setup

1. Create a free project at [Supabase](https://supabase.com/dashboard).
2. In **SQL Editor**, run [`supabase/migrations/001_vector_knowledge_base.sql`](supabase/migrations/001_vector_knowledge_base.sql). This enables pgvector, creates `knowledge_chunks`, RLS restrictions, an HNSW cosine index, and `match_knowledge_chunks`.
3. Find the project URL under **Project Settings → API**.
4. Copy the server-only service-role key from **Project Settings → API keys**. Never use this key in browser JavaScript.
5. Open **Connect** at the top of the project page to copy the Postgres connection string (`DATABASE_URL`). Use the pooler connection where appropriate for hosted/serverless clients.

The SQL vector dimension is 768 and must match `EMBEDDING_DIMENSION=768`. Changing it requires a migration and re-embedding every document.

## Local configuration

```bash
cp .env.example .env
```

Required for web retrieval (the database URL is supported for direct admin/migration tooling but the runtime client uses the Supabase URL and service-role key):

```text
GEMINI_API_KEY=
GEMINI_CHAT_MODEL=gemini-3.8-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=
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

## Test

```bash
pytest -q
```

Tests mock Gemini, HTTP/PDF behavior, and Supabase, so they do not consume API credits.

## Render deployment

Create a Python Web Service and configure:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Environment: every web retrieval variable listed above
- Health URL: `/`

Add secrets in **Render Dashboard → Service → Environment**. Do not commit them. Deploy starts only the Flask web application. Run ingestion separately as a manual/admin job from a trusted environment with the four source variables set. A restart or redeploy must not scrape and re-embed the sources.

To refresh content safely, run the ingestion command again. Unchanged chunks are skipped. Inspect failures and retrieval quality before relying on newly indexed content.

## Security and answer behavior

- `SUPABASE_SERVICE_ROLE_KEY` and `DATABASE_URL` are backend-only secrets and must never appear in HTML, frontend JavaScript, logs, or responses.
- RLS denies table access to `anon` and `authenticated`; only the backend service role can write or invoke the match function.
- Source and model text is rendered with DOM `textContent`, not unsanitized `innerHTML`.
- If no evidence passes the configured threshold, VietRights returns a cautious no-evidence message instead of generating a legal answer.
- VietRights provides general information, not professional legal advice.

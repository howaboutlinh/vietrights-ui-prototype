# Render deployment checklist

1. Create the Supabase project and run `supabase/migrations/001_vector_knowledge_base.sql`.
2. Create a Render Python Web Service from this repository.
3. Set build command to `pip install -r requirements.txt`.
4. Set start command to `gunicorn app:app`.
5. Add `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3.6-flash`, `GEMINI_EMBEDDING_MODEL`, `DATABASE_URL`, `RAG_MATCH_COUNT`, `RAG_MATCH_THRESHOLD`, and `EMBEDDING_DIMENSION` in Render Environment. Remove any old `GEMINI_CHAT_MODEL` override such as `gemini-2.5-flash`. `DATABASE_URL` must be the Supabase Session Pooler URL and uses the psycopg 3 driver (`postgresql+psycopg://`).
6. Deploy and verify `/` and `/analyze`.
7. Configure the four `KNOWLEDGE_SOURCE_*` values only in the trusted environment used for ingestion.
8. Run `python scripts/ingest_knowledge.py --dry-run`, review the output, then run the real ingestion command manually.

The build/deploy command starts the web app only. Knowledge ingestion is a separate admin operation and must not run automatically on deploy or restart. Never expose or log `DATABASE_URL`. Schema changes come from the SQL migration; do not use `db.create_all()` in production.

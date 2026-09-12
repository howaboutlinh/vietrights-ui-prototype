# Render deployment checklist

1. Create the Supabase project and run `supabase/migrations/001_vector_knowledge_base.sql`.
2. Create a Render Python Web Service from this repository.
3. Set build command to `pip install -r requirements.txt`.
4. Set start command to `gunicorn app:app`.
5. Add `GEMINI_API_KEY`, `GEMINI_CHAT_MODEL`, `GEMINI_EMBEDDING_MODEL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `RAG_MATCH_COUNT`, `RAG_MATCH_THRESHOLD`, and `EMBEDDING_DIMENSION` in Render Environment.
6. Deploy and verify `/` and `/analyze`.
7. Configure the four `KNOWLEDGE_SOURCE_*` values only in the trusted environment used for ingestion.
8. Run `python scripts/ingest_knowledge.py --dry-run`, review the output, then run the real ingestion command manually.

The build/deploy command starts the web app only. Knowledge ingestion is a separate admin operation and must not run automatically on deploy or restart. Never expose the Supabase service-role key or database URL to the browser.

# Knowledge source registry

This folder is reserved for official and organizer-provided workplace-rights source material for future RAG use.

## Rules

1. Only official or organizer-provided sources should be stored here.
2. Do not add fake legal content, invented rules, or unverified summaries.
3. Do not scrape or invent rules yet.
4. This folder is for source records and extracted material only, not for generated legal advice.

## Preferred source categories

- Fair Work Ombudsman
- SafeWork NSW
- Department of Home Affairs
- RMWC / organizer-provided migrant worker resources

## Required metadata for each source entry

Each source should record:

- title
- organisation
- topic
- source URL
- extracted content
- last checked date

## JSON source format

Use one JSON file per source topic with this structure:

```json
{
  "title": "...",
  "organisation": "...",
  "topic": "...",
  "source_url": "...",
  "last_checked": "YYYY-MM-DD",
  "content": [
    "...",
    "..."
  ]
}
```

Rules:

- Do not invent legal rules or URLs.
- If a verified official source is not available locally yet, use empty `content` arrays with TODO placeholders only.
- Do not add fake wage figures.
- Keep files simple, factual, and human-editable.

## Notes for future RAG work

- The knowledge base should grow from authoritative Australian sources only.
- Keep extracted text short, plain, and attributable to the original source.
- Only add material when it is directly supported by an official or organizer-provided source.

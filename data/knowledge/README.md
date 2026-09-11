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

## Example structure

Use one file per source or one source index file per topic. Keep entries factual and traceable to the original page.

Example metadata:

```yaml
- title: "Example official source"
  organisation: "Fair Work Ombudsman"
  topic: "minimum wages and entitlements"
  source_url: "https://example.gov.au/page"
  extracted_content: "Brief factual notes from the official source only."
  last_checked: "2026-09-11"
```

## Notes for future RAG work

- The knowledge base should grow from authoritative Australian sources only.
- Keep extracted text short, plain, and attributable to the original source.
- Only add material when it is directly supported by an official or organizer-provided source.

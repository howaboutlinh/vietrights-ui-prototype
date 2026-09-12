# Approved local knowledge sources

Place manually downloaded official `.pdf` or UTF-8 `.txt` files here when an official site blocks respectful automated retrieval. Do not copy search snippets or unofficial summaries.

Optionally add a provenance sidecar named `<filename>.metadata.json`:

```json
{
  "source_url": "https://official.example/page",
  "source_name": "Official organisation",
  "document_title": "Official document title"
}
```

Configure `KNOWLEDGE_SOURCE_N=data/sources/<filename>` and run `--dry-run` before real ingestion.

## VietRights manual downloads currently required

The ingestion environment cannot respectfully retrieve these resources. Download them in a normal browser without automation:

1. [Fair Work migrant-rights PDF](https://www.fairwork.gov.au/sites/default/files/migration/723/visa-holders-and-migrant-workers-workplace-rights-and-entitlements.pdf) → `data/sources/fair-work-migrant-rights.pdf`
2. [Fair Work record-keeping and pay-slips PDF](https://www.fairwork.gov.au/sites/default/files/migration/723/Record-keeping-and-pay-slips.pdf) → `data/sources/fair-work-record-keeping-pay-slips.pdf`
3. Open [Home Affairs help and reporting protections](https://immi.homeaffairs.gov.au/visas/employing-and-sponsoring-someone/migrant-worker-protections/help-reporting-protections-workplace-justice-visa), use the browser's **Print → Save as PDF**, and save as `data/sources/home-affairs-workplace-justice-visa.pdf`.

Do not rename the provided `.metadata.json` sidecars; they preserve the original official URL and organisation for citations.

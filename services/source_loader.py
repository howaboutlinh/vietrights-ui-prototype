"""Safe same-domain HTML/PDF discovery and extraction."""

from __future__ import annotations

import io
import json
import logging
import re
import time
from collections import deque
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from services.chunking import DocumentSection, SourceDocument, normalize_text

logger = logging.getLogger(__name__)
USER_AGENT = "VietRightsKnowledgeBot/1.0 (+workplace-rights research; respectful crawler)"
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024


class SourceLoadError(RuntimeError):
    """Raised for a source response that cannot be safely processed."""


def load_local_document(path_value: str | Path) -> SourceDocument:
    """Load an approved local PDF/text source and optional provenance sidecar."""
    path = Path(path_value).expanduser().resolve()
    approved_root = (Path(__file__).resolve().parents[1] / "data" / "sources").resolve()
    if approved_root not in path.parents:
        raise SourceLoadError("Local knowledge files must be stored under data/sources/.")
    if not path.is_file():
        raise SourceLoadError(f"Local source file does not exist: {path.name}")
    if path.suffix.lower() not in {".pdf", ".txt"}:
        raise SourceLoadError("Local sources must be PDF or UTF-8 text files.")
    sidecar = path.with_suffix(path.suffix + ".metadata.json")
    metadata: dict[str, str] = {}
    if sidecar.is_file():
        try:
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SourceLoadError(f"Invalid provenance sidecar: {sidecar.name}") from exc
    source_url = str(metadata.get("source_url") or path.as_uri())
    source_name = str(metadata.get("source_name") or "Approved local source")
    if path.suffix.lower() == ".pdf":
        document = extract_pdf(path.read_bytes(), source_url, source_name)
    else:
        text = normalize_text(path.read_text(encoding="utf-8"))
        document = SourceDocument(source_name, source_url, path.stem, "text", [DocumentSection(text=text)] if text else [])
    if metadata.get("document_title"):
        document.document_title = str(metadata["document_title"])
    return document


def _source_name(url: str) -> str:
    return urlparse(url).hostname or "Unknown source"


def _allowed(url: str, approved_host: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and (parsed.hostname or "").lower() == approved_host.lower()


def extract_html(html: str, url: str, source_name: str | None = None) -> tuple[SourceDocument, list[str]]:
    """Extract useful structured text and same-domain page/PDF links from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for selector in ("script", "style", "nav", "footer", "noscript", "svg", "form", "[class*='cookie']", "[id*='cookie']"):
        for node in soup.select(selector):
            node.decompose()
    title = normalize_text(soup.title.get_text(" ", strip=True) if soup.title else url)
    root = soup.find("main") or soup.find("article") or soup.body or soup
    sections: list[DocumentSection] = []
    heading = ""
    seen: set[str] = set()
    for node in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "table"]):
        text = normalize_text(node.get_text(" ", strip=True))
        if not text:
            continue
        if node.name.startswith("h"):
            heading = text
            continue
        fingerprint = text.casefold()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        sections.append(DocumentSection(text=text, section_title=heading))
    approved_host = urlparse(url).hostname or ""
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        resolved = urldefrag(urljoin(url, anchor["href"]))[0]
        if _allowed(resolved, approved_host):
            links.append(resolved)
    return SourceDocument(source_name or _source_name(url), url, title, "html", sections), list(dict.fromkeys(links))


def extract_pdf(data: bytes, url: str, source_name: str | None = None) -> SourceDocument:
    """Extract non-empty PDF pages while retaining page attribution."""
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise SourceLoadError(f"Unable to open PDF: {url}") from exc
    metadata = reader.metadata or {}
    title = normalize_text(str(metadata.get("/Title") or Path(urlparse(url).path).name or url))
    page_texts: list[tuple[int, str]] = []
    for number, page in enumerate(reader.pages, start=1):
        try:
            text = normalize_text(page.extract_text() or "")
        except Exception as exc:
            logger.warning("PDF page extraction failed domain=%s page=%s error=%s", _source_name(url), number, type(exc).__name__)
            continue
        if text:
            page_texts.append((number, text))
    # Remove likely repeated headers/footers, but only in documents with enough pages
    # to avoid deleting legitimate short-document content.
    edge_counts: dict[str, int] = {}
    if len(page_texts) >= 3:
        for _, text in page_texts:
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            for line in set(lines[:2] + lines[-2:]):
                edge_counts[line] = edge_counts.get(line, 0) + 1
    repeated = {line for line, count in edge_counts.items() if count >= max(3, len(page_texts) // 2)}
    sections: list[DocumentSection] = []
    for number, text in page_texts:
        cleaned = "\n".join(line for line in text.splitlines() if line.strip() not in repeated)
        cleaned = normalize_text(cleaned)
        if cleaned:
            sections.append(DocumentSection(text=cleaned, section_title=f"Page {number}", page_number=number))
    return SourceDocument(source_name or _source_name(url), url, title, "pdf", sections)


class SourceCrawler:
    """Bounded crawler that never leaves the configured source root's domain."""

    def __init__(self, timeout: int = 30, max_depth: int = 2, max_pages: int = 40, session: requests.Session | None = None):
        self.timeout = timeout
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _robots(self, root_url: str) -> RobotFileParser:
        parsed = urlparse(root_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        response = self.session.get(robots_url, timeout=self.timeout)
        if response.status_code in {401, 403}:
            raise SourceLoadError(f"Robots policy could not be accessed for {parsed.hostname}; refusing to crawl.")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines() if response.ok else [])
        return parser

    def crawl(self, root_url: str) -> tuple[list[SourceDocument], list[tuple[str, str]]]:
        parsed = urlparse(root_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise SourceLoadError(f"Invalid source URL: {root_url}")
        robots = self._robots(root_url)
        crawl_delay = robots.crawl_delay(USER_AGENT) or robots.crawl_delay("*") or 0
        request_delay = max(0.5, float(crawl_delay))
        queue = deque([(urldefrag(root_url)[0], 0)])
        visited: set[str] = set()
        documents: list[SourceDocument] = []
        failures: list[tuple[str, str]] = []
        while queue and len(visited) < self.max_pages:
            url, depth = queue.popleft()
            if url in visited or not _allowed(url, parsed.hostname):
                continue
            if not robots.can_fetch(USER_AGENT, url):
                failures.append((url, "Blocked by robots.txt"))
                continue
            visited.add(url)
            try:
                if documents or failures:
                    time.sleep(request_delay)
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                declared_size = int(response.headers.get("content-length", "0") or 0)
                if declared_size > MAX_DOWNLOAD_BYTES or len(response.content) > MAX_DOWNLOAD_BYTES:
                    raise SourceLoadError(f"Source exceeds {MAX_DOWNLOAD_BYTES} byte download limit: {url}")
                content_type = response.headers.get("content-type", "").lower()
                is_pdf = "application/pdf" in content_type or urlparse(url).path.lower().endswith(".pdf")
                if is_pdf:
                    documents.append(extract_pdf(response.content, url, parsed.hostname))
                elif "html" in content_type or not content_type:
                    document, links = extract_html(response.text, url, parsed.hostname)
                    if document.sections:
                        documents.append(document)
                    if depth < self.max_depth:
                        for link in links:
                            if link not in visited:
                                queue.append((link, depth + 1))
            except Exception as exc:
                logger.warning("Source extraction failed domain=%s error=%s", parsed.hostname, type(exc).__name__)
                failures.append((url, str(exc)))
        return documents, failures

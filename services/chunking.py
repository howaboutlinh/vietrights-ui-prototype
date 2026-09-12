"""Structure-aware text cleaning, hashing and chunking."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable


@dataclass
class DocumentSection:
    """A source section extracted from HTML or PDF."""

    text: str
    section_title: str = ""
    page_number: int | None = None


@dataclass
class SourceDocument:
    """An extracted source document before chunking."""

    source_name: str
    source_url: str
    document_title: str
    document_type: str
    sections: list[DocumentSection] = field(default_factory=list)


@dataclass
class KnowledgeChunk:
    """A normalized, attributable unit ready for embedding."""

    source_name: str
    source_url: str
    document_title: str
    document_type: str
    section_title: str
    content: str
    content_hash: str
    chunk_index: int
    metadata: dict[str, Any]


def normalize_text(text: str) -> str:
    """Normalize whitespace without altering legal figures or punctuation."""
    text = str(text or "").replace("\u00a0", " ").replace("\u00ad", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def content_hash(content: str, source_url: str) -> str:
    """Create a stable duplicate key from normalized content and source URL."""
    material = f"{source_url.strip()}\n{normalize_text(content)}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text) if part.strip()]


def _units(sections: Iterable[DocumentSection], max_words: int) -> list[tuple[str, str, int | None]]:
    units: list[tuple[str, str, int | None]] = []
    for section in sections:
        for paragraph in re.split(r"\n\s*\n", normalize_text(section.text)):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if len(paragraph.split()) <= max_words:
                units.append((paragraph, section.section_title, section.page_number))
                continue
            buffer: list[str] = []
            count = 0
            for sentence in _sentences(paragraph):
                words = sentence.split()
                if len(words) > max_words:
                    if buffer:
                        units.append((" ".join(buffer), section.section_title, section.page_number))
                        buffer, count = [], 0
                    for start in range(0, len(words), max_words):
                        units.append((" ".join(words[start:start + max_words]), section.section_title, section.page_number))
                    continue
                if buffer and count + len(words) > max_words:
                    units.append((" ".join(buffer), section.section_title, section.page_number))
                    buffer, count = [], 0
                buffer.append(sentence)
                count += len(words)
            if buffer:
                units.append((" ".join(buffer), section.section_title, section.page_number))
    return units


def chunk_document(
    document: SourceDocument,
    target_tokens: int = 850,
    overlap_tokens: int = 125,
    max_tokens: int = 1000,
) -> list[KnowledgeChunk]:
    """Chunk by sections/paragraphs using a conservative words-to-token estimate."""
    if not 0 <= overlap_tokens < target_tokens <= max_tokens:
        raise ValueError("Chunk sizes must satisfy 0 <= overlap < target <= max.")
    target_words = max(1, int(target_tokens * 0.72))
    overlap_words = max(0, int(overlap_tokens * 0.72))
    max_words = max(1, int(max_tokens * 0.72))
    unit_words = max(1, min(max_words - overlap_words, target_words - overlap_words))
    units = _units(document.sections, unit_words)
    chunks: list[KnowledgeChunk] = []
    current: list[str] = []
    current_words = 0
    section_title = ""
    page_number: int | None = None

    def flush() -> None:
        nonlocal current, current_words
        if not current:
            return
        text = normalize_text("\n\n".join(current))
        index = len(chunks)
        metadata: dict[str, Any] = {
            "source_name": document.source_name,
            "source_url": document.source_url,
            "document_title": document.document_title,
            "document_type": document.document_type,
            "section_title": section_title,
            "chunk_index": index,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        if page_number is not None:
            metadata["page_number"] = page_number
        chunks.append(KnowledgeChunk(
            source_name=document.source_name,
            source_url=document.source_url,
            document_title=document.document_title,
            document_type=document.document_type,
            section_title=section_title,
            content=text,
            content_hash=content_hash(text, document.source_url),
            chunk_index=index,
            metadata=metadata,
        ))
        overlap = text.split()[-overlap_words:] if overlap_words else []
        current = [" ".join(overlap)] if overlap else []
        current_words = len(overlap)

    for text, unit_section, unit_page in units:
        words = len(text.split())
        if current and current_words + words > target_words:
            flush()
        current.append(text)
        current_words += words
        section_title = unit_section or section_title
        page_number = unit_page if unit_page is not None else page_number
    flush()
    return chunks

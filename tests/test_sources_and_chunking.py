from types import SimpleNamespace
from services.chunking import DocumentSection, SourceDocument, chunk_document, content_hash
from services.source_loader import extract_html, extract_pdf
import services.source_loader as source_loader

def test_html_extraction_removes_navigation_and_keeps_structure():
    html = """<html><head><title>Pay rights</title></head><body><nav>Menu</nav><main>
    <h1>Minimum pay</h1><p>Workers must receive the applicable minimum rate.</p>
    <script>secret()</script><a href='/guide.pdf'>PDF</a></main></body></html>"""
    document, links = extract_html(html, "https://example.gov.au/pay")
    assert document.document_title == "Pay rights"
    assert document.sections[0].section_title == "Minimum pay"
    assert "Menu" not in document.sections[0].text
    assert links == ["https://example.gov.au/guide.pdf"]

def test_pdf_extraction_preserves_page_number(monkeypatch):
    class Page:
        def extract_text(self): return "Official payslip guidance"
    monkeypatch.setattr("services.source_loader.PdfReader", lambda _: SimpleNamespace(metadata={"/Title": "Guide"}, pages=[Page()]))
    document = extract_pdf(b"pdf", "https://example.gov.au/guide.pdf")
    assert document.document_title == "Guide"
    assert document.sections[0].page_number == 1

def test_chunk_overlap_and_maximum_size():
    text = " ".join(f"word{i}." for i in range(1800))
    document = SourceDocument("Official", "https://example.gov.au/a", "Guide", "html", [DocumentSection(text, "Pay")])
    chunks = chunk_document(document, target_tokens=200, overlap_tokens=30, max_tokens=240)
    assert len(chunks) > 2
    assert all(len(chunk.content.split()) <= int(240 * 0.72) for chunk in chunks)
    assert set(chunks[0].content.split()[-20:]).intersection(chunks[1].content.split()[:30])

def test_duplicate_content_hash_is_stable():
    assert content_hash("same   content", "https://example/a") == content_hash("same content", "https://example/a")
    assert content_hash("same content", "https://example/a") != content_hash("same content", "https://example/b")

def test_approved_local_text_source_with_provenance(tmp_path, monkeypatch):
    fake_module = tmp_path / "services" / "source_loader.py"
    source_dir = tmp_path / "data" / "sources"
    source_dir.mkdir(parents=True)
    source_file = source_dir / "official.txt"
    source_file.write_text("Official workplace safety guidance.", encoding="utf-8")
    sidecar = source_dir / "official.txt.metadata.json"
    sidecar.write_text(
        '{"source_url":"https://example.gov.au/rights","source_name":"Official agency","document_title":"Worker rights"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(source_loader, "__file__", str(fake_module))
    document = source_loader.load_local_document(source_file)
    assert document.document_type == "text"
    assert document.source_url == "https://example.gov.au/rights"
    assert document.sections[0].text

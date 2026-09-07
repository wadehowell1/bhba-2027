"""Stage 2b — deterministic ATS-readiness validation.

Does NOT ask a model to "act as an ATS". Round-trips the generated file through
real text extractors and asserts the machine sees what the human sees.
"""
from __future__ import annotations
import re, subprocess, zipfile
from dataclasses import dataclass, field
from pathlib import Path
from docx import Document

REQUIRED_HEADINGS = ["PROFESSIONAL SUMMARY", "CORE COMPETENCIES",
                     "PROFESSIONAL EXPERIENCE", "EDUCATION & CERTIFICATIONS"]
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


@dataclass
class AtsReport:
    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    extracted_chars: int = 0
    bullet_count_source: int = 0
    bullet_count_extracted: int = 0
    estimated_pages: int = 1

    def fail(self, m): self.passed = False; self.errors.append(m)
    def warn(self, m): self.warnings.append(m)


def extract_docx_text(path: Path) -> str:
    return "\n".join(p.text for p in Document(path).paragraphs)


def validate(docx_path: Path) -> AtsReport:
    r = AtsReport()
    doc = Document(docx_path)

    # 1. Structural killers
    if doc.tables:
        r.fail(f"contains {len(doc.tables)} table(s) — tables scramble parse order")
    for section in doc.sections:
        for part in (section.header, section.footer):
            if any(p.text.strip() for p in part.paragraphs):
                r.fail("content in header/footer — most parsers discard it")
    with zipfile.ZipFile(docx_path) as z:
        names = z.namelist()
        if any(n.startswith("word/media/") for n in names):
            r.warn("embedded image present — carries no parseable text")
        xml = z.read("word/document.xml").decode("utf8", "ignore")
        if "<w:txbxContent" in xml:
            r.fail("text box detected — contents are frequently dropped")
        if "<w:cols" in xml and 'w:num="2"' in xml:
            r.fail("multi-column layout detected — interleaves the reading order")

    # 2. Round-trip extraction
    text = extract_docx_text(docx_path)
    r.extracted_chars = len(text)
    if r.extracted_chars < 1200:
        r.fail(f"only {r.extracted_chars} chars extracted — content is not machine-readable")

    head = text[:300]
    if not EMAIL.search(head):
        r.fail("email not found in first 300 extracted characters")
    if not PHONE.search(head):
        r.fail("phone not found in first 300 extracted characters")

    # 3. Headings recovered verbatim
    upper = text.upper()
    for h in REQUIRED_HEADINGS:
        if h not in upper:
            r.fail(f"section heading not recovered: {h}")

    # 4. Bullet fidelity — nothing lost between source and extraction
    src_bullets = [p.text.strip() for p in doc.paragraphs
                   if p.style.name.startswith("List") and p.text.strip()]
    r.bullet_count_source = len(src_bullets)
    r.bullet_count_extracted = sum(1 for b in src_bullets if b in text)
    if r.bullet_count_source != r.bullet_count_extracted:
        r.fail(f"bullet loss: {r.bullet_count_source} written, "
               f"{r.bullet_count_extracted} recovered")
    if r.bullet_count_source < 8:
        r.warn(f"only {r.bullet_count_source} bullets — thin for a senior CV")

    # 4b. Length. A senior CV runs two pages; recruiters do not read a third.
    est_pages = max(1, round(r.extracted_chars / 3200))
    r.estimated_pages = est_pages
    if est_pages > 2:
        r.fail(f"CV runs ~{est_pages} pages ({r.extracted_chars} chars, "
               f"{r.bullet_count_source} bullets) — trim to 2")

    # 5. Reading order
    if text.find("PROFESSIONAL SUMMARY") > text.find("PROFESSIONAL EXPERIENCE"):
        r.fail("reading order inverted: summary extracted after experience")
    return r


def to_pdf(docx_path: Path) -> Path | None:
    """LibreOffice headless conversion for the human-readable copy."""
    try:
        profile = Path.home() / ".ats_soffice_profile"
        subprocess.run(["soffice", "--headless", "--norestore",
                        f"-env:UserInstallation=file://{profile}",
                        "--convert-to", "pdf",
                        "--outdir", str(docx_path.parent), str(docx_path)],
                       check=True, capture_output=True, timeout=240)
        pdf = docx_path.with_suffix(".pdf")
        return pdf if pdf.exists() else None
    except Exception:
        return None

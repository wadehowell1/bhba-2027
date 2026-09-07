"""Stage 2a — ATS-safe CV renderer.

Hard structural rules (these are what actually break ATS parsers, not keyword density):
  single column · no tables · no text boxes · no header/footer content ·
  standard section headings · contact details in the first text block ·
  bullets as real list paragraphs · common embedded font

Input is a TailoringPlan: achievement IDs + optional rephrasings. The renderer
pulls statement text from achievements.yaml. It cannot render a bullet that has
no bank record behind it.
"""
from __future__ import annotations
import json, re
from dataclasses import dataclass, field
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from .bank import load_bank, load_profile, achievement_index, employment_index

STANDARD_HEADINGS = ["Professional Summary", "Core Competencies", "Professional Experience",
                     "Education & Certifications", "Additional Information"]
NUM = re.compile(r"\d[\d,.]*\s*(?:%|k\b|m\b|bn\b|\+)?", re.I)


@dataclass
class RoleBlock:
    employment_id: str
    achievement_ids: list[str]
    rephrasings: dict[str, str] = field(default_factory=dict)  # ach_id -> reworded text


@dataclass
class TailoringPlan:
    job_title: str
    company: str
    headline: str                       # e.g. "Operational Excellence & Transformation Leader"
    summary: str                        # 3-4 sentences, must contain no unsourced numbers
    competencies: list[str]             # drawn from skills inventory + matched tags
    roles: list[RoleBlock]
    source_job_id: str = ""

    @staticmethod
    def from_json(raw: str | dict) -> "TailoringPlan":
        d = json.loads(raw) if isinstance(raw, str) else raw
        return TailoringPlan(
            job_title=d["job_title"], company=d["company"], headline=d["headline"],
            summary=d["summary"], competencies=d["competencies"],
            source_job_id=d.get("source_job_id", ""),
            roles=[RoleBlock(r["employment_id"], r["achievement_ids"], r.get("rephrasings", {}))
                   for r in d["roles"]],
        )


class FabricationError(ValueError):
    pass


def low_confidence_claims(plan: "TailoringPlan") -> list[str]:
    """Records used by the plan whose figures are disputed or single-sourced.

    Not fabrication — the claim exists in the bank — but it has not been
    confirmed by the candidate, so it must never leave without review.
    `CHECK` means the master CVs disagree; `medium` means one source only.
    """
    ach = achievement_index()
    out: list[str] = []
    for role in plan.roles:
        for aid in role.achievement_ids:
            rec = ach.get(aid)
            if not rec:
                continue
            c = rec.get("confidence", "high")
            if c in ("CHECK", "medium"):
                out.append(f"{aid}:{c}")
    return out


def verify_plan(plan: TailoringPlan) -> list[str]:
    """Reject any plan that invents evidence. Returns list of flags; empty == clean."""
    flags: list[str] = []
    ach, emp = achievement_index(), employment_index()

    for role in plan.roles:
        if role.employment_id not in emp:
            flags.append(f"unknown_employment:{role.employment_id}")
        for aid in role.achievement_ids:
            rec = ach.get(aid)
            if rec is None:
                flags.append(f"unknown_achievement:{aid}")
                continue
            if rec.get("employment_id") not in (role.employment_id, None):
                flags.append(f"achievement_attributed_to_wrong_role:{aid}")
            reworded = role.rephrasings.get(aid)
            if reworded:
                orig_nums = set(NUM.findall(rec["statement"]))
                new_nums = set(NUM.findall(reworded))
                invented = new_nums - orig_nums
                if invented:
                    flags.append(f"invented_metric:{aid}:{sorted(invented)}")

    summary_nums = set(NUM.findall(plan.summary))
    bank_nums: set[str] = set()
    for rec in ach.values():
        bank_nums |= set(NUM.findall(rec["statement"]))
    bank_nums |= {"20", "20+"}  # years of experience, stated on master CV
    for n in summary_nums:
        if n.strip() not in {b.strip() for b in bank_nums}:
            flags.append(f"unsourced_number_in_summary:{n.strip()}")
    return flags


def _style(doc: Document) -> None:
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)
    st.paragraph_format.space_after = Pt(3)
    st.paragraph_format.line_spacing = 1.05
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Inches(0.5)
        s.left_margin = s.right_margin = Inches(0.6)


def _heading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text.upper())
    r.bold = True
    r.font.size = Pt(11)
    r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)


def render(plan: TailoringPlan, out_path: Path, strict: bool = True) -> tuple[Path, list[str]]:
    flags = verify_plan(plan)
    if flags and strict:
        raise FabricationError("; ".join(flags))

    prof, bank = load_profile(), load_bank()
    ident = prof["identity"]
    ach, emp = achievement_index(), employment_index()

    doc = Document()
    _style(doc)

    # --- Contact block: plain paragraphs, first content in the document ---
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"{ident['full_name'].upper()}, {ident['credentials_suffix']}")
    r.bold = True
    r.font.size = Pt(17)

    contact = f"{ident['location_city']}, {ident['location_country']} | {ident['phone']} | {ident['email']}"
    if ident.get("linkedin") and ident["linkedin"] != "ASK":
        contact += f" | {ident['linkedin']}"
    cp = doc.add_paragraph(contact)
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER

    hp = doc.add_paragraph()
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hr = hp.add_run(plan.headline)
    hr.bold = True
    hr.font.size = Pt(11)

    _heading(doc, "Professional Summary")
    doc.add_paragraph(plan.summary)

    _heading(doc, "Core Competencies")
    # Comma-delimited line, NOT a table — tables are the #1 ATS parse failure.
    doc.add_paragraph(" | ".join(plan.competencies))

    _heading(doc, "Professional Experience")
    for role in plan.roles:
        e = emp[role.employment_id]
        rp = doc.add_paragraph()
        rp.paragraph_format.space_before = Pt(8)
        rr = rp.add_run(f"{e['title']}")
        rr.bold = True
        rr.font.size = Pt(11)
        meta = doc.add_paragraph()
        mr = meta.add_run(f"{e['employer']} | {e['location']} | {e['start']} – {e['end']}")
        mr.italic = True
        for aid in role.achievement_ids:
            text = role.rephrasings.get(aid) or ach[aid]["statement"]
            doc.add_paragraph(text, style="List Bullet")

    _heading(doc, "Education & Certifications")
    core = [c for c in bank["credentials"] if c.get("tier", "core") == "core"]
    extra = [c for c in bank["credentials"] if c.get("tier", "core") != "core"]
    for c in core:
        line = c["name"] + (f" — {c['issuer']}" if c.get("issuer") else "")
        doc.add_paragraph(line, style="List Bullet")
    if extra:
        # Supplementary training belongs on one line, not as ten more bullets.
        doc.add_paragraph("Further professional development: "
                          + "; ".join(c["name"] for c in extra))

    _heading(doc, "Additional Information")
    svc = [a for a in bank["achievements"] if a["id"] == "ACH-060"]
    if svc:
        doc.add_paragraph(svc[0]["statement"], style="List Bullet")
    doc.add_paragraph("Work authorisation: Jamaican citizen. Open to relocation and remote engagement.",
                      style="List Bullet")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    return out_path, flags

"""PDF renderer — same TailoringPlan, pure-Python, real text layer.

Avoids any LibreOffice/system dependency and guarantees the PDF's extracted
text order matches the document order (which soffice conversion does not).
"""
from __future__ import annotations
from pathlib import Path
from fpdf import FPDF
from .bank import load_bank, load_profile, achievement_index, employment_index
from .render_cv import TailoringPlan, verify_plan, FabricationError

NAVY = (31, 58, 95)

_SUBS = {"\u2014": "-", "\u2013": "-", "\u2019": "'", "\u2018": "'",
         "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00a0": " ",
         "\u2022": "-", "\u25c6": "-", "\u2192": "->", "\u00b7": "-"}


def _s(text: str) -> str:
    """Map typographic characters to the PDF core-font range."""
    for k, v in _SUBS.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")



class CV(FPDF):
    def header(self):  # intentionally empty: no header content (ATS rule)
        pass

    def footer(self):  # intentionally empty: no footer content (ATS rule)
        pass


def _h(pdf: CV, text: str) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.ln(2.5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 5.5, _s(text.upper()), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*NAVY)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(1.5)
    pdf.set_text_color(0, 0, 0)


def render_pdf(plan: TailoringPlan, out_path: Path, strict: bool = True) -> tuple[Path, list[str]]:
    flags = verify_plan(plan)
    if flags and strict:
        raise FabricationError("; ".join(flags))

    prof, bank = load_profile(), load_bank()
    ident = prof["identity"]
    ach, emp = achievement_index(), employment_index()

    pdf = CV(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.set_margins(15, 12, 15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 17)
    pdf.cell(0, 8, _s(f"{ident['full_name'].upper()}, {ident['credentials_suffix']}"),
             align="C", new_x="LMARGIN", new_y="NEXT")

    contact = f"{ident['location_city']}, {ident['location_country']}  |  {ident['phone']}  |  {ident['email']}"
    if ident.get("linkedin") and ident["linkedin"] != "ASK":
        contact += f"  |  {ident['linkedin']}"
    pdf.set_font("Helvetica", "", 9.5)
    pdf.cell(0, 5, _s(contact), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 5, _s(plan.headline), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)

    _h(pdf, "Professional Summary")
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 4.4, _s(plan.summary))

    _h(pdf, "Core Competencies")
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 4.4, _s("  |  ".join(plan.competencies)))

    _h(pdf, "Professional Experience")
    for role in plan.roles:
        e = emp[role.employment_id]
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 4.8, _s(e["title"]))
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 4.4, _s(f"{e['employer']}  |  {e['location']}  |  {e['start']} - {e['end']}"))
        pdf.set_font("Helvetica", "", 9.5)
        for aid in role.achievement_ids:
            text = role.rephrasings.get(aid) or ach[aid]["statement"]
            _bullet(pdf, text)

    _h(pdf, "Education & Certifications")
    pdf.set_font("Helvetica", "", 9.5)
    core = [c for c in bank["credentials"] if c.get("tier", "core") == "core"]
    extra = [c for c in bank["credentials"] if c.get("tier", "core") != "core"]
    for c in core:
        _bullet(pdf, c["name"] + (f" - {c['issuer']}" if c.get("issuer") else ""))
    if extra:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 4.4, _s("Further professional development: "
                                  + "; ".join(c["name"] for c in extra)))

    _h(pdf, "Additional Information")
    pdf.set_font("Helvetica", "", 9.5)
    svc = [a for a in bank["achievements"] if a["id"] == "ACH-060"]
    if svc:
        _bullet(pdf, svc[0]["statement"])
    _bullet(pdf, "Work authorisation: Jamaican citizen. Open to relocation and remote engagement.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    return out_path, flags


def _bullet(pdf: CV, text: str) -> None:
    """Hanging-indent bullet. Plain hyphen so text extraction never garbles."""
    indent = 4.0
    usable = pdf.w - pdf.l_margin - pdf.r_margin - indent
    pdf.set_x(pdf.l_margin)
    pdf.cell(indent, 4.4, "-")
    pdf.multi_cell(usable, 4.4, _s(text))
    pdf.set_x(pdf.l_margin)

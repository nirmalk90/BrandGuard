"""Render the Round 2 submission PDF with ReportLab and Pillow."""
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "BrandGuard-AI-Round-2.pdf"
WIDTH, HEIGHT = A4
INK = HexColor("#0c2137")
MUTED = HexColor("#475c71")
TEAL = HexColor("#007468")
LIGHT = HexColor("#dce6ef")

styles = {
    "kicker": ParagraphStyle("kicker", fontName="Helvetica-Bold", fontSize=10, leading=15, textColor=TEAL, spaceAfter=10),
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=32, leading=36, textColor=INK, spaceAfter=9),
    "deck": ParagraphStyle("deck", fontName="Helvetica", fontSize=12, leading=17, textColor=MUTED, spaceAfter=17),
    "head": ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=INK, spaceBefore=13, spaceAfter=5),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=15.3, textColor=INK, spaceAfter=8),
    "caption": ParagraphStyle("caption", fontName="Helvetica", fontSize=9, leading=13, textColor=MUTED, alignment=TA_CENTER, spaceBefore=7, spaceAfter=10),
}


def paragraph(text, style="body"):
    return Paragraph(text, styles[style])


def screenshot(filename, crop=None, max_width=455):
    source = ROOT / "docs" / "screenshots" / filename
    with PILImage.open(source) as original:
        picture = original.convert("RGB")
    if crop:
        picture = picture.crop(crop)
    width, height = picture.size
    encoded = BytesIO()
    picture.save(encoded, format="PNG")
    encoded.seek(0)
    return Image(encoded, width=max_width, height=height * max_width / width)


def section(title, text):
    return [paragraph(title, "head"), paragraph(text)]


def footer(canvas, document):
    canvas.setTitle("BrandGuard AI | CodeNova India 2026 Round 2")
    canvas.setAuthor("CoderX")
    canvas.setStrokeColor(LIGHT)
    canvas.line(46, 46, WIDTH - 46, 46)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(46, 30, "CODERX  /  CODENOVA INDIA 2026")
    canvas.drawRightString(WIDTH - 46, 30, str(document.page))


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=46, rightMargin=46, topMargin=46, bottomMargin=62)
    story = [
        paragraph("ROUND 2  /  THE BUILD", "kicker"),
        paragraph("BrandGuard AI", "title"),
        paragraph("Intelligent Brand Governance<br/>CoderX | CodeNova India 2026 | Organised by Inkloom AI", "deck"),
        *section("Problem and users", "Marketing teams publish across channels with input from employees, agencies and AI tools. Manual review makes it easy for inconsistent product names, unsupported guarantees and outdated pricing to enter campaigns. BrandGuard AI gives creators, brand admins and reviewers a shared record from draft to decision."),
        *section("What we built", "The NovaTech demo includes an editable brand profile, approved sources, versioned rules, TXT/PDF/DOCX intake, evidence-backed findings, editable revisions, human approvals and analytics based on saved activity."),
        Spacer(1, 8),
        screenshot("workspace.png", (0, 0, 1280, 835)),
        paragraph("The fictional NovaTech workspace starts with real, empty submission metrics.", "caption"),
        *section("Judge workflow", "Open Try Live Demo, analyze the sample, edit the draft and run the checks again. Request approval, switch to Reviewer and record a decision. Review History preserves the original draft, revised content and approval rationale after reload."),
        PageBreak(),
        paragraph("EVIDENCE AND APPROVAL", "kicker"),
        paragraph("From flagged copy to sign-off", "title"),
        paragraph("The sample triggers four findings for terminology, accuracy, a market-wide price claim, and a monthly subscription price below the approved starting price."),
        screenshot("findings.png", (0, 0, 1280, 850), max_width=418),
        paragraph("Original copy, severity counts, and findings with policy evidence and draft corrections.", "caption"),
        screenshot("approval.png", (0, 0, 1280, 825), max_width=418),
        paragraph("The approved second version, reviewer identity and recorded decision rationale.", "caption"),
        PageBreak(),
        paragraph("TECHNICAL IMPLEMENTATION", "kicker"),
        paragraph("Architecture and verification", "title"),
        *section("System architecture", "React and TypeScript compile with Vite. FastAPI serves the dashboard and REST API from one origin. SQLAlchemy persists workspaces, policy sources, rules, content versions, assessments and approvals in SQLite or PostgreSQL. Alembic applies the schema."),
        *section("AI and responsible use", "Deterministic checks use the NovaTech messaging guidelines and product fact sheet. Optional model assistance uses keyword-ranked evidence and requires per-review consent. The server validates cited rule IDs and verbatim excerpts, falls back to rules on provider errors, and marks model observations for human review. Demo sessions use opaque cookies, workspace-scoped access and server-enforced sample roles."),
        *section("Testing performed", "The TypeScript and production frontend build passed. Seven API tests covered dynamic policy, evidence, draft and revision persistence, role enforcement, isolation, document validation and model fallback. Two Chromium scenarios passed on SQLite and PostgreSQL, covering the judge journey and mobile rule creation."),
        *section("Changes from the Round 1 concept", "Round 2 implements a text-first governance workflow. The recommended Next.js and split deployment were simplified to a Vite frontend and one FastAPI service. Keyword retrieval replaced vector infrastructure for this round. Production organisation sign-in, OCR and multimodal checks are deferred. Live provider inference and the public deployment still need verification."),
        *section("Round 3 proposals", "<b>Multimodal Brand Verification</b> adds logo, layout and accessibility checks.<br/><b>Publishing and Collaboration Integrations</b> bring reviews into CMS and design workflows.<br/><b>Advanced Governance Intelligence</b> adds cross-campaign analysis, policy audits and recurring rule-conflict detection."),
        *section("Repository, demo and credits", "The repository and public demo links are pending publication. CoderX is the submitting team. Individual team names and contributions are pending confirmation."),
    ]
    document.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    main()

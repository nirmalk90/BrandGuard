"""Build the evidence-based Round 3 product report."""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Flowable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/BrandGuard-AI-Round-3.pdf'
W, H = A4
INK = colors.HexColor('#10273E')
TEAL = colors.HexColor('#007D72')
MUTED = colors.HexColor('#516477')
LIGHT = colors.HexColor('#E9F3F2')
LINE = colors.HexColor('#D5E1E9')
STYLES = {
    'eyebrow': ParagraphStyle('eyebrow', fontName='Helvetica-Bold', fontSize=9, leading=13, textColor=TEAL, spaceAfter=10),
    'title': ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=28, leading=32, textColor=INK, spaceAfter=12),
    'deck': ParagraphStyle('deck', fontName='Helvetica', fontSize=12, leading=17, textColor=MUTED, spaceAfter=16),
    'head': ParagraphStyle('head', fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=INK, spaceBefore=12, spaceAfter=5, keepWithNext=True),
    'body': ParagraphStyle('body', fontName='Helvetica', fontSize=10.2, leading=14.4, textColor=INK, spaceAfter=8),
    'small': ParagraphStyle('small', fontName='Helvetica', fontSize=8.6, leading=12, textColor=MUTED, spaceAfter=6),
    'feature': ParagraphStyle('feature', fontName='Helvetica', fontSize=9.4, leading=13.5, textColor=INK, spaceAfter=2.4),
}

def p(text, kind='body'):
    return Paragraph(text, STYLES[kind])

def heading(kicker, title, deck=None):
    rows = [p(kicker.upper(), 'eyebrow'), p(title, 'title')]
    if deck:
        rows.append(p(deck, 'deck'))
    return rows

def section(title, text):
    return [p(title, 'head'), p(text)]

def callout(title, text):
    t=Table([[p(title, 'eyebrow')], [p(text)]], colWidths=[W-96])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),LIGHT),('LEFTPADDING',(0,0),(-1,-1),13),
        ('RIGHTPADDING',(0,0),(-1,-1),13),('TOPPADDING',(0,0),(-1,0),12),('BOTTOMPADDING',(0,-1),(-1,-1),8)]))
    return t

class Architecture(Flowable):
    def __init__(self):
        Flowable.__init__(self)
        self.width=W-96
        self.height=98
    def draw(self):
        c=self.canv
        labels=[('WEB APP','React + TypeScript'),('SERVICE','FastAPI REST API'),('STORAGE','SQLAlchemy + DB')]
        bw=147
        for i,(title,subtitle) in enumerate(labels):
            x=i*176
            c.setFillColor(LIGHT);c.roundRect(x,37,bw,52,7,fill=1,stroke=0)
            c.setFillColor(TEAL);c.setFont('Helvetica-Bold',8);c.drawString(x+11,70,title)
            c.setFillColor(INK);c.setFont('Helvetica',9);c.drawString(x+11,51,subtitle)
            if i<2:
                c.setStrokeColor(TEAL);c.line(x+bw+4,63,x+bw+24,63)
                c.line(x+bw+20,66,x+bw+24,63);c.line(x+bw+20,60,x+bw+24,63)
        c.setFillColor(MUTED);c.setFont('Helvetica',9)
        c.drawString(0,16,'Analysis workers: document extraction / English OCR / OpenCV / optional chat API')

def footer(c,doc):
    c.setTitle('BrandGuard AI | CodeNova India 2026 | Round 3')
    c.setAuthor('CoderX')
    c.setStrokeColor(LINE);c.line(48,43,W-48,43)
    c.setFont('Helvetica',8);c.setFillColor(MUTED)
    c.drawString(48,28,'CODERX  /  CODENOVA INDIA 2026  /  19 NOV 2026')
    c.drawRightString(W-48,28,f'{doc.page:02d}')

def main():
    story=[]
    story += heading('Round 3 / Product report', 'BrandGuard AI', 'Intelligent Brand Governance<br/>CoderX | Team leader: Nirmal Kumar')
    story += [callout('FROM DRAFT TO HUMAN APPROVAL', 'Review marketing copy and artwork against approved brand guidance, resolve findings with evidence, and preserve the exact material behind each decision.'),Spacer(1,12)]
    story += section('Problem and users', 'Marketing teams publish copy and visual assets across channels. Inconsistent terminology, unsupported promises and outdated facts can escape manual review. BrandGuard gives creators, brand administrators and reviewers a shared workflow from draft to recorded decision.')
    story += section('Product workflow', 'An administrator adds approved sources, rules, colours and logos. A creator submits copy, documents or artwork. BrandGuard analyses the material and presents grounded findings and highlighted image regions. The creator revises or explains a finding, then requests approval. A reviewer approves, rejects or requests changes. History and campaign analytics preserve the evidence.')
    story += section('Project links', '<b>Live application:</b> <link href="https://brandguard-ai-pt15.onrender.com/" color="#007D72">brandguard-ai-pt15.onrender.com</link><br/><b>Source repository:</b> <link href="https://github.com/nirmalk90/BrandGuard" color="#007D72">github.com/nirmalk90/BrandGuard</link>')
    story += section('Deployment verification', 'On 19 November, the live service passed three Chromium scenarios, six additional API scenario groups and a governance browser exercise. Copy and artwork review, revisions, approvals, history, mobile navigation and campaign evidence were exercised. The WordPress API passed; a real WordPress editor and persistence across service restart remain unverified.')
    story += [callout('JUDGE ACCESS / REVIEW COPY', 'Open the live URL and click Try Live Demo. No key is required. Use the demo role selector to test creator, reviewer and administrator actions in an isolated sample workspace. Individual contribution credits still require confirmation before submission.')]
    story += [PageBreak()]

    story += heading('01 / Feature inventory','Working product capabilities','Core workflows verified locally and on the public demo. Private team access was tested locally; the real WordPress editor remains unverified.')
    features=[
        'Isolated sample workspaces and role-based creator, reviewer and admin access.',
        'Private access-key sign-in and fixed roles for team workspaces.',
        'Editable brand profiles, messaging guidance and approved colours.',
        'Approved guideline and product-fact source management.',
        'TXT, PDF and DOCX imports for sources and marketing drafts.',
        'Configurable rules with versions, activation status and validity dates.',
        'Checks for prohibited phrases and required terminology.',
        'Checks for unsupported promotional claims and pricing contradictions.',
        'Source-linked findings with severity, explanations and suggested corrections.',
        'PNG and JPG artwork uploads with English OCR.',
        'Checks of artwork text against configured brand rules.',
        'Logo comparison with uploaded approved brand assets.',
        'Detection of potentially off-brand colour regions.',
        'Combined artwork and marketing-copy review.',
        'Highlighted image regions linked to individual findings.',
        'Saved drafts, editable revisions and repeat analysis.',
        'Suggested corrections that creators can copy or apply to copy drafts.',
        'Finding dismissal and contesting with recorded reasons.',
        'Approval queues and reviewer approval, rejection or change requests.',
        'Revision-specific decisions with actor, rationale and timestamp.',
        'Previous approval states superseded by changed copy or artwork.',
        'Historical content, artwork, findings and visual-reference versions.',
        'Analytics for statuses, review activity, severity and frequently flagged rules.',
        'Campaign assignment and reassignment of submissions.',
        'Recurring violations and conflicts grouped by rule and rule version.',
        'Rule-version finding rates and percentage-point comparisons.',
        'Links from campaign patterns to exact underlying assessments.',
        'Deduplication of repeated analysis within a draft revision.',
        'Responsive desktop and mobile navigation.'
    ]
    story += [p(f'{i:02d} &nbsp; {escape(s)}','feature') for i,s in enumerate(features,1)]
    story += section('Implemented, with verification outstanding','The WordPress plugin and optional external AI assistance are implemented. WordPress backend behaviour and AI fallback are tested; the real WordPress editor workflow and live model-provider behaviour are not yet verified.')
    story += [PageBreak()]

    story += heading('02 / Technical implementation','Architecture and data flow')
    story += [Architecture()]
    story += section('Components and APIs','React and TypeScript compile through Vite. FastAPI serves both the frontend and REST API from one origin. HttpOnly session cookies identify the workspace, and the server enforces role permissions and workspace scope. SQLAlchemy persists profiles, sources, rules, submissions, versions, reviews, findings, assets and decisions; Alembic manages schema migrations.')
    story += section('Analysis pipeline','PyMuPDF and python-docx extract document text. An isolated Tesseract worker extracts English text and coordinates from artwork. OpenCV searches for approved logo shapes, compares colours and identifies large potentially off-brand colour regions. Deterministic rules check terminology, required phrases, selected claims and approved facts. Findings retain policy and source references, evidence status, severity and image coordinates where available.')
    story += section('Models and integrations','Optional chat-completions assistance sends the draft and keyword-ranked policy excerpts only after per-review consent. Structured output is checked for recognised rule IDs and genuine quotations, and provider failures retain deterministic results. The WordPress plugin uses a server-side REST proxy and connection key to submit editor snapshots and retrieve decisions. Its real editor integration remains unverified.')
    story += section('Persistence and infrastructure','Local verification used SQLite; live tests exercised the deployed database through the API. The repository includes Docker and Render configuration for a service with persistent PostgreSQL, migration-on-startup, HTTPS-secured cookies, a health endpoint and an unprivileged container user. The public demo workflow passes live tests. Its database configuration, persistence through restart and backup recovery were not established by this run.')
    story += section('Hardest implementation challenge','Keeping approval tied to the exact reviewed material required immutable revisions, preserved artwork references and generation checks that reject stale updates. WordPress snapshots use SHA-256 fingerprints across the title, block content, excerpt, slug and featured-media ID. Changed snapshots need review, and concurrent identical submissions reuse one review. Campaign aggregation similarly avoids counting repeat analysis as new recurrence.')
    story += [PageBreak()]

    story += heading('03 / Commitments and delivery','The three improvements','Assessed against the broader promises recorded in the Round 2 project report.')
    story += section('1. Multimodal Brand Verification | Partial','<b>Committed:</b> Detect logos, compare layouts and colours with brand rules, and add visual accessibility checks.<br/><b>Delivered:</b> PNG/JPG upload, English OCR, checks of embedded text, approved-logo comparison, colour-region warnings, highlighted findings and combined copy/artwork review. Local and deployed API/browser checks passed.<br/><b>Not delivered:</b> Layout comparison and visual accessibility measurements such as text contrast. Implementation narrowed to OCR, logos and colours; dedicated layout and accessibility rules are absent. Difficult images still require human inspection.')
    story += section('2. Publishing and Collaboration Integrations | Partial','<b>Committed:</b> Bring reviews into CMS publishing, design handoffs and shared collaboration workflows.<br/><b>Delivered:</b> A WordPress plugin, exact-draft snapshots, decision retrieval, changed-draft detection, connection-key revocation and named team access with fixed roles. Local and live backend tests passed.<br/><b>Not delivered or verified:</b> No design-tool integration or dedicated design-handoff workflow. The real WordPress editor scenario remains unverified because a connected test installation was not configured. Scope focused on WordPress and shared review permissions. The plugin advises editors; it does not block publishing.')
    story += section('3. Advanced Governance Intelligence | Partial','<b>Committed:</b> Track policy changes, identify recurring rule conflicts and compare compliance patterns across campaigns.<br/><b>Delivered:</b> Campaign dashboards group violations and conflicts by rule version, compare finding rates and link to exact reviews. Repeat analysis is deduplicated. Local and deployed API/browser checks passed.<br/><b>Not delivered:</b> Direct cross-campaign comparison and a complete policy edit audit with before/after specifications and editor identity. Scope focused on recurrence within a campaign and assessment evidence. Finding-rate changes are observations, not proof of causal improvement.')
    story += section('Other work after Round 2','Refreshed dashboard styling, navigation and responsive behaviour; expanded the Python suite from 7 to 14 passing tests and browser coverage from 2 to 3 passing scenarios; updated deployment configuration, dependency constraints and operational documentation. No application changes were required during the recorded verification pass.')
    story += [PageBreak()]

    story += heading('04 / Verification','Testing and known limits','Local verification: 18 November 2026. Public deployment functional tests: 19 November 2026.')
    table=Table([[p('<b>Check</b>'),p('<b>Result</b>'),p('<b>Coverage</b>')],
        [p('Local Python / pytest'),p('14 passed'),p('API behaviour, persistence, permissions, OCR, visual findings, governance, WordPress snapshots and migration preservation.')],
        [p('Live Chromium / Playwright'),p('3 passed<br/>1 skipped'),p('Review-to-approval journey, mobile rule creation and artwork/history links. Real WordPress test skipped.')],
        [p('Build and dependencies'),p('Passed'),p('TypeScript check, Vite production build and Python dependency consistency.')],
        [p('Extra live checks'),p('6 API groups + browser passed'),p('Imports, validation, permissions, isolation, PNG/JPG, governance and WordPress API; browser filters, rates and evidence links.')]],
        colWidths=[110,80,W-96-190],hAlign='LEFT')
    table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),LIGHT),('LINEBELOW',(0,0),(-1,-1),0.5,LINE),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story += [table]
    story += section('What the checks established','Tests exercised dynamic rules, grounded evidence, workspace isolation, role enforcement, stale-update rejection, document validation, revisions, finding disputes and approval persistence. Improvement tests used real OCR and synthetic reference artwork, checked recoloured logos and verified immutable artwork history. WordPress API tests covered snapshot changes, retries, concurrency, isolation and revocation. A malformed simulated model response exercised fallback.')
    story += section('Manual and browser observations','Manual inspection covered the desktop dashboard and campaign empty state. The additional browser exercise confirmed two affected revisions still counted as two after repeat analysis, and a rule-version finding rate changed from 100% to 0% with a displayed -100 percentage-point difference. Evidence links opened the exact assessment. Formal external user testing has not been conducted.')
    story += section('What was found and fixed','No blocking failures were found in the tested live flows, and no application-code fixes were required. The extra browser exercise captured no JavaScript exceptions or failed requests. Real WordPress editor testing, private team sign-in on the live service and persistence across restart/redeploy remain outstanding. Live PNG/JPG upload plus review took about five seconds per synthetic sample; this was not a load test.')
    story += section('Known imperfections','English-only OCR and heuristic visual matching can miss stylised text, rotated logos or complex photographic content. Missing or uncertain matches require human review. WordPress fingerprints cover editor fields and featured-media selection, not later changes to the file behind a media ID, theme output or third-party fields. Live optional model inference is unverified. Historical assessments without evaluated-rule inventories show unknown coverage.')
    story += [PageBreak()]

    story += heading('05 / Next steps','Roadmap and team record','Priorities are ordered by dependency and the evidence needed before wider use.')
    roadmap=[
        ('1. Validate the deployed review workflow','For creators and reviewers: connect a disposable WordPress site, verify submission/approval/edit detection, and test HTTPS access, PostgreSQL migrations, persistence and recovery. Needs a staging service, infrastructure access and repeatable integration tests.'),
        ('2. Pilot with a small marketing team','Observe creators, a brand manager and a reviewer using their own consented guidelines and artwork. Measure review time, false positives, missed issues and overrides. Needs sample content, feedback sessions and an evaluation log.'),
        ('3. Add layout and visual accessibility checks','For designers and brand reviewers: implement configurable placement zones, minimum margins and text-contrast warnings. Needs explicit visual constraints, reference designs and a labelled set of acceptable and problematic artwork.'),
        ('4. Add full policy audits and campaign comparisons','For brand managers: preserve every edit with author, timestamp and before/after values, then compare selected campaigns by rule version. Needs audit records, comparison views and clear treatment of different review volumes.'),
        ('5. Integrate design handoffs','For designers and agencies: start with Figma frame export, source links and version-bound review status. Needs API access, secure authorisation and reliable mapping from each submitted design to its decision.')
    ]
    for title,text in roadmap:
        story += section(title,text)
    story += section('Team and individual contributions','<b>Team:</b> CoderX<br/><b>Team leader:</b> Nirmal Kumar<br/>Individual roles and contribution credits have not been confirmed. Complete this record using the team\'s actual work before submitting this review copy.')
    story += section('Development assistance and reused components','Codex assisted with the readiness review, test execution and preparation of this report. The implementation uses the libraries and runtimes named in the architecture section. Confirm any additional significant AI development tools or reused project components before final submission.')
    story += [p('Evidence basis: repository implementation and tests; local readiness audit and 19 November live test report; original Round 2 project report; team-provided scope descriptions and live URL. This report distinguishes implemented behaviour, tested behaviour and outstanding verification.','small')]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=46,bottomMargin=58)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(OUT)

if __name__=='__main__':
    main()

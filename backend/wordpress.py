from hashlib import sha256
from html.parser import HTMLParser
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend import db
from backend.demo import new_id
from backend.engine import review
from backend.workflow import policy, rule_snapshot, save_review

router = APIRouter(prefix="/api/wordpress", tags=["WordPress"])


class Snapshot(BaseModel):
    # Preserve whitespace, block markup and Unicode exactly as sent by the editor.
    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=1000)
    content: str = Field(max_length=200000)
    excerpt: str = Field(max_length=20000)
    slug: str = Field(max_length=1000)
    featured_media: int = Field(ge=0, le=2147483647)


class Draft(BaseModel):
    snapshot: Snapshot
    campaign: str = Field(default="Unassigned", min_length=1, max_length=100)


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif tag == "img" and not self.hidden:
            self.parts.append(" " + (dict(attrs).get("alt") or "") + " ")
        elif tag in ("p", "br", "div", "li", "h1", "h2", "h3", "h4", "blockquote", "td"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        elif tag in ("p", "li", "div"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def fingerprint(snapshot):
    # Length-prefixed UTF-8 fields make this independent of JSON serialisation in PHP.
    digest = sha256()
    for name in ("title", "content", "excerpt", "slug", "featured_media"):
        value = str(snapshot[name]).encode()
        digest.update(str(len(value)).encode() + b":" + value)
    return digest.hexdigest()


def credential(authorization: Annotated[str | None, Header()] = None):
    token = (authorization or "").removeprefix("Bearer ")
    if not authorization or not authorization.startswith("Bearer ") or len(token) != 43:
        raise HTTPException(401, "A WordPress connection key is required.")
    with db.engine.connect() as conn:
        integration = conn.execute(select(db.connections).where(
            db.connections.c.token_hash == sha256(token.encode()).hexdigest())).one_or_none()
    if not integration:
        raise HTTPException(401, "The WordPress connection key is invalid or has been revoked.")
    return integration


def decision(conn, integration, post_id, digest):
    base = (db.posts.c.connection_id == integration.id, db.posts.c.post_id == post_id)
    row = conn.execute(select(db.posts.c.submission_id, db.submissions.c.status)
        .select_from(db.posts.join(db.submissions)).where(*base, db.posts.c.digest == digest)).first()
    if not row:
        has_history = conn.execute(select(db.posts.c.id).where(*base).limit(1)).first()
        return dict(status="NEEDS_REVIEW" if has_history else "NOT_SUBMITTED", digest=digest)
    comment = conn.execute(select(db.actions.c.comment).where(db.actions.c.submission_id == row.submission_id,
        db.actions.c.action == row.status).order_by(db.actions.c.created_at.desc()).limit(1)).scalar()
    return dict(status=row.status, comment=comment or "", submission_id=row.submission_id, digest=digest)


@router.get("/posts/{post_id}")
def status(post_id: int, digest: Annotated[str, Query(pattern=r"^[a-f0-9]{64}$")],
           integration=Depends(credential)):
    with db.engine.connect() as conn:
        return decision(conn, integration, post_id, digest)


@router.post("/posts/{post_id}")
def submit(post_id: int, draft: Draft, integration=Depends(credential)):
    if not 0 < post_id <= 2147483647:
        raise HTTPException(422, "A saved WordPress post ID is required.")
    snapshot = draft.snapshot.model_dump()
    digest = fingerprint(snapshot)
    with db.engine.connect() as conn:
        existing = decision(conn, integration, post_id, digest)
        if "submission_id" in existing:
            return existing
        rules = policy(conn, integration.workspace_id)
    parser = VisibleText()
    parser.feed("\n".join(snapshot[field] for field in ("title", "content", "excerpt")))
    parser.close()
    content = "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())
    if len(content) > 20000 or not content:
        raise HTTPException(422, "Send a draft containing between 1 and 20,000 visible characters.")
    result = review(content, rules, False)
    submission_id, version_id = new_id(), new_id()
    try:
        with db.engine.begin() as conn:
            conn.execute(db.submissions.insert().values(id=submission_id, workspace_id=integration.workspace_id,
                title=snapshot["title"].strip()[:160] or f"WordPress post {post_id}", content_type="WordPress draft",
                platform="WordPress", creator="WordPress editor", campaign=draft.campaign.strip() or "Unassigned",
                status="PENDING_APPROVAL", revision=1, generation=1))
            conn.execute(db.versions.insert().values(id=version_id, submission_id=submission_id, number=1,
                content=content, content_hash=sha256(content.encode()).hexdigest()))
            save_review(conn, version_id, result, rule_snapshot(rules))
            conn.execute(db.posts.insert().values(id=new_id(), submission_id=submission_id, snapshot=snapshot,
                connection_id=integration.id, post_id=post_id, digest=digest))
            conn.execute(db.actions.insert().values(id=new_id(), submission_id=submission_id, version_id=version_id,
                actor="WordPress editor", action="PENDING_APPROVAL", comment="Sent from the WordPress block editor."))
            return decision(conn, integration, post_id, digest)
    except IntegrityError:
        # Two editors can submit the same snapshot concurrently. The losing transaction rolls back entirely.
        with db.engine.connect() as conn:
            existing = decision(conn, integration, post_id, digest)
            if "submission_id" in existing:
                return existing
        raise

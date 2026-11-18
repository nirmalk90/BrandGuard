import hashlib
import os
import secrets
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from typing import Literal
from zipfile import ZipFile, ZIP_DEFLATED

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from backend import artwork, governance, wordpress
from backend.db import assets, connections, engine, members, now, rules, sessions, sources, submissions, workspaces
from backend.team import token_hash
from backend.demo import DEMO_CONTENT, new_id, seed_workspace
from backend.engine import ai_available
from backend.schemas import Contest, Decision, Profile, RevisionInput, Role, Rule, Source, SubmissionInput, Submit
from backend.uploads import extract
from backend.workflow import actor_name, analyze, contest, detail, metrics, policy, require, save_draft, scoped, transition

app = FastAPI(title="BrandGuard AI", version="2.0.0")
app.include_router(wordpress.router)
COOKIE = "brandguard_demo"
DIST = Path(__file__).resolve().parents[1] / "dist"


class RequestSizeLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        headers = Headers(scope=scope)
        limit = 6 * 1024**2 if scope["path"] in {"/api/artwork", "/api/logos", "/api/extract"} else 2 * 1024**2
        length = headers.get("content-length")
        if length and (len(length) > 12 or not length.isdecimal() or int(length) > limit):
            return await JSONResponse({"detail": "Request body exceeds the upload limit."}, 413)(scope, receive, send)
        consumed = 0

        async def limited_receive():
            nonlocal consumed
            message = await receive()
            consumed += len(message.get("body", b""))
            if consumed > limit:
                raise HTTPException(413, "Request body exceeds the upload limit.")
            return message

        await self.app(scope, limited_receive, send)


app.add_middleware(RequestSizeLimit)


class RoleInput(BaseModel):
    role: Role


def cookie_id(request):
    value = request.cookies.get(COOKIE, "")
    if len(value) != 43:
        return None
    return hashlib.sha256(value.encode()).hexdigest()


def session_for(request: Request):
    session_id = cookie_id(request)
    query = select(sessions, members.c.name).select_from(sessions.outerjoin(members)).where(
        sessions.c.id == session_id, sessions.c.created_at >= now() - timedelta(days=30))
    if not demo_enabled():
        query = query.where(members.c.id.is_not(None))
    with engine.connect() as connection:
        actor = connection.execute(query).one_or_none()
    if actor is None:
        raise HTTPException(401, "Sign in to your workspace to continue.")
    return actor


def session_payload(connection, actor):
    profile = connection.execute(select(workspaces.c.profile).where(
        workspaces.c.id == actor.workspace_id,
    )).scalar_one()
    return dict(role=actor.role, actor=actor_name(actor), profile=profile, demo=actor.member_id is None,
                workspace_id=actor.workspace_id, ai_available=ai_available(), sample=DEMO_CONTENT)


@app.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        connection.execute(select(workspaces.c.id).limit(1))
    return {"status": "ok"}


@app.post("/api/demo", status_code=201)
def start_demo(response: Response):
    if not demo_enabled():
        raise HTTPException(403, "Demo workspaces are disabled.")
    token = secrets.token_urlsafe(32)
    token_id = hashlib.sha256(token.encode()).hexdigest()
    with engine.begin() as connection:
        workspace_id = seed_workspace(connection)
        actor = connection.execute(sessions.insert().values(
            id=token_id, workspace_id=workspace_id, role="creator",
        ).returning(*sessions.c)).one()
        payload = session_payload(connection, actor)
    set_cookie(response, token)
    return payload


def demo_enabled():
    return os.getenv("BRANDGUARD_MODE", "demo") == "demo"


def set_cookie(response, token):
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict",
                        secure=os.getenv("SECURE_COOKIES", "0" if demo_enabled() else "1") == "1",
                        max_age=30 * 86400)


@app.get("/api/access")
def access():
    return {"demo": demo_enabled()}


class Login(BaseModel):
    key: str = Field(min_length=43, max_length=43)


@app.post("/api/login")
def login(data: Login, response: Response):
    with engine.begin() as conn:
        member = conn.execute(select(members).where(members.c.id == token_hash(data.key)).with_for_update()).one_or_none()
        if not member:
            raise HTTPException(401, "Invalid workspace key.")
        token = secrets.token_urlsafe(32)
        conn.execute(sessions.insert().values(id=token_hash(token), workspace_id=member.workspace_id,
                                              role=member.role, member_id=member.id))
        actor = conn.execute(select(sessions, members.c.name).join(members).where(sessions.c.id == token_hash(token))).one()
        set_cookie(response, token)
        return session_payload(conn, actor)


@app.post("/api/logout", status_code=204)
def logout(response: Response, actor=Depends(session_for)):
    with engine.begin() as conn:
        conn.execute(sessions.delete().where(sessions.c.id == actor.id))
    response.delete_cookie(COOKIE)


@app.get("/api/session")
def get_session(actor=Depends(session_for)):
    with engine.connect() as connection:
        return session_payload(connection, actor)


@app.put("/api/demo/role")
def switch_role(data: RoleInput, actor=Depends(session_for)):
    if actor.member_id or not demo_enabled():
        raise HTTPException(403, "Team members have fixed roles.")
    with engine.begin() as connection:
        updated = connection.execute(sessions.update().where(
            sessions.c.id == actor.id,
        ).values(role=data.role).returning(*sessions.c)).one()
        return session_payload(connection, updated)


@app.put("/api/brand")
def edit_brand(data: Profile, actor=Depends(session_for)):
    require(actor, "admin")
    with engine.begin() as connection:
        previous = connection.execute(select(workspaces.c.profile).where(
            workspaces.c.id == actor.workspace_id).with_for_update()).scalar_one()
        changed = any(previous[key].lower() != getattr(data, key).lower() for key in ("primary_color", "secondary_color"))
        connection.execute(workspaces.update().where(
            workspaces.c.id == actor.workspace_id,
        ).values(profile=data.model_dump(), palette_version=workspaces.c.palette_version + int(changed)))
        return session_payload(connection, actor)


@app.get("/api/knowledge")
def knowledge(actor=Depends(session_for)):
    with engine.connect() as connection:
        documents = list(connection.execute(select(sources).where(
            sources.c.workspace_id == actor.workspace_id,
        ).order_by(sources.c.created_at, sources.c.id)).mappings())
        return {"rules": policy(connection, actor.workspace_id), "sources": documents}


@app.post("/api/sources", status_code=201)
def create_source(data: Source, actor=Depends(session_for)):
    require(actor, "admin")
    with engine.begin() as connection:
        return connection.execute(sources.insert().values(
            id=new_id(), workspace_id=actor.workspace_id, version=1, **data.model_dump(),
        ).returning(*sources.c)).mappings().one()


@app.post("/api/rules", status_code=201)
@app.put("/api/rules/{rule_id}")
def save_rule(data: Rule, rule_id: str | None = None, actor=Depends(session_for)):
    require(actor, "admin")
    with engine.begin() as connection:
        scoped(connection, sources, actor, data.source_id)
        values = dict(source_id=data.source_id, active=data.active,
                      spec=data.model_dump(mode="json"), updated_at=now())
        if rule_id:
            scoped(connection, rules, actor, rule_id)
            statement = rules.update().where(
                rules.c.id == rule_id, rules.c.workspace_id == actor.workspace_id,
            ).values(version=rules.c.version + 1, **values)
        else:
            statement = rules.insert().values(
                id=new_id(), workspace_id=actor.workspace_id, version=1, **values,
            )
        return connection.execute(statement.returning(*rules.c)).mappings().one()


@app.delete("/api/rules/{rule_id}", status_code=204)
def deactivate(rule_id: str, actor=Depends(session_for)):
    require(actor, "admin")
    with engine.begin() as connection:
        rule = scoped(connection, rules, actor, rule_id)
        connection.execute(rules.update().where(
            rules.c.id == rule_id, rules.c.workspace_id == actor.workspace_id,
        ).values(active=False, version=rules.c.version + 1,
                 updated_at=now(), spec={**rule["spec"], "active": False}))


@app.post("/api/extract")
async def upload(file: UploadFile, actor=Depends(session_for)):
    require(actor, "creator", "admin")
    return await extract(file)


@app.get("/api/submissions")
def list_submissions(status: Literal["PENDING_APPROVAL"] | None = None, actor=Depends(session_for)):
    query = select(submissions).where(submissions.c.workspace_id == actor.workspace_id)
    if status:
        query = query.where(submissions.c.status == status)
    with engine.connect() as connection:
        return list(connection.execute(query.order_by(
            submissions.c.updated_at.desc(), submissions.c.id,
        ).limit(250)).mappings())


@app.post("/api/submissions", status_code=201)
def create_submission(data: SubmissionInput, actor=Depends(session_for)):
    return analyze(actor, data)


@app.post("/api/submissions/draft", status_code=201)
def create_draft(data: SubmissionInput, actor=Depends(session_for)):
    return save_draft(actor, data)


@app.get("/api/submissions/{submission_id}")
def read_submission(submission_id: str, actor=Depends(session_for)):
    with engine.connect() as connection:
        return detail(connection, actor, submission_id)


@app.post("/api/submissions/{submission_id}/reanalyze")
def revise(submission_id: str, data: RevisionInput, actor=Depends(session_for)):
    return analyze(actor, data, submission_id)


@app.post("/api/submissions/{submission_id}/submit-for-approval")
def submit(submission_id: str, data: Submit, actor=Depends(session_for)):
    return transition(actor, submission_id, data.generation, "PENDING_APPROVAL", "")


@app.post("/api/submissions/{submission_id}/decision")
def decide(submission_id: str, data: Decision, actor=Depends(session_for)):
    return transition(actor, submission_id, data.generation, data.action, data.comment)


@app.put("/api/submissions/{submission_id}/findings/{finding_id}")
def update_finding(submission_id: str, finding_id: str, data: Contest, actor=Depends(session_for)):
    return contest(actor, submission_id, finding_id, data)


@app.get("/api/analytics")
def analytics(actor=Depends(session_for)):
    with engine.connect() as connection:
        return metrics(connection, actor)


@app.get("/api/campaigns")
def campaigns(actor=Depends(session_for)):
    with engine.connect() as conn:
        return conn.execute(select(submissions.c.campaign).where(submissions.c.workspace_id == actor.workspace_id)
                            .distinct().order_by(submissions.c.campaign)).scalars().all()


@app.get("/api/governance")
def campaign_governance(campaign: str, actor=Depends(session_for)):
    with engine.connect() as conn:
        return governance.patterns(conn, actor, campaign)


@app.get("/api/governance/evidence")
def pattern_evidence(campaign: str, rule_id: str, version: int = Query(ge=1), offset: int = Query(0, ge=0),
                     flag: Literal["all", "flagged", "violation", "conflict", "disputed"] = "all", actor=Depends(session_for)):
    with engine.connect() as conn:
        links = governance.patterns(conn, actor, campaign, rule_key=(rule_id, version))
    if flag != "all":
        links = [link for link in links if flag in link["flags"]]
    return {"total": len(links), "reviews": links[offset:offset + 25]}


class Campaign(Submit):
    campaign: str = Field(min_length=1, max_length=100)


@app.put("/api/submissions/{submission_id}/campaign")
def set_campaign(submission_id: str, data: Campaign, actor=Depends(session_for)):
    require(actor, "admin", "creator")
    with engine.begin() as conn:
        scoped(conn, submissions, actor, submission_id)
        changed = conn.execute(submissions.update().where(submissions.c.id == submission_id,
            submissions.c.generation == data.generation).values(campaign=data.campaign, updated_at=now(),
            generation=data.generation + 1))
        if not changed.rowcount:
            raise HTTPException(409, "This submission changed. Reload it and try again.")
        return detail(conn, actor, submission_id)


@app.post("/api/artwork", status_code=201)
def upload_artwork(file: UploadFile, actor=Depends(session_for)):
    require(actor, "creator")
    return artwork.save_upload(actor, file, "artwork")


@app.get("/api/assets/{asset_id}")
def image_asset(asset_id: str, actor=Depends(session_for)):
    with engine.connect() as conn:
        asset = scoped(conn, assets, actor, asset_id)
        return Response(asset["image"], media_type=asset["mime"])


@app.get("/api/logos")
def approved_logos(actor=Depends(session_for)):
    with engine.connect() as conn:
        return artwork.logos(conn, actor)


@app.post("/api/logos", status_code=201)
def add_logo(file: UploadFile, actor=Depends(session_for)):
    require(actor, "admin")
    return artwork.save_upload(actor, file, "logo")


@app.delete("/api/logos/{asset_id}", status_code=204)
def retire_logo(asset_id: str, actor=Depends(session_for)):
    require(actor, "admin")
    with engine.begin() as conn:
        artwork.bump_logos(conn, actor)
        if not conn.execute(assets.update().where(assets.c.id == asset_id,
            assets.c.workspace_id == actor.workspace_id, assets.c.kind == "logo", assets.c.active.is_(True))
            .values(active=False)).rowcount:
            raise HTTPException(404, "Approved logo unavailable.")


@app.get("/api/integrations/wordpress")
def wordpress_connection(actor=Depends(session_for)):
    require(actor, "admin")
    with engine.connect() as conn:
        return {"connected": bool(conn.execute(select(connections.c.token_hash).where(
            connections.c.workspace_id == actor.workspace_id)).scalar())}


@app.post("/api/integrations/wordpress")
def issue_wordpress_key(actor=Depends(session_for)):
    require(actor, "admin")
    token = secrets.token_urlsafe(32)
    with engine.begin() as conn:
        conn.execute(workspaces.update().where(workspaces.c.id == actor.workspace_id).values(id=workspaces.c.id))
        if not conn.execute(connections.update().where(connections.c.workspace_id == actor.workspace_id)
                            .values(token_hash=token_hash(token))).rowcount:
            conn.execute(connections.insert().values(id=new_id(), workspace_id=actor.workspace_id,
                                                     token_hash=token_hash(token)))
    return {"key": token}


@app.delete("/api/integrations/wordpress", status_code=204)
def revoke_wordpress(actor=Depends(session_for)):
    require(actor, "admin")
    with engine.begin() as conn:
        conn.execute(connections.update().where(connections.c.workspace_id == actor.workspace_id).values(token_hash=None))


@app.get("/api/integrations/wordpress/plugin.zip")
def download_plugin(actor=Depends(session_for)):
    require(actor, "admin")
    buf = BytesIO()
    with ZipFile(buf, "w", ZIP_DEFLATED) as archive:
        for name in ("brandguard.php", "editor.js"):
            archive.write(DIST.parent / "wordpress" / "brandguard" / name, "brandguard/" + name)
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="brandguard.zip"'})


@app.middleware("http")
async def protect_api(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


if (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})

    @app.get("/brandguard.svg", include_in_schema=False)
    def logo():
        return FileResponse(DIST / "brandguard.svg")

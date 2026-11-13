import hashlib
import os
import secrets
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select, text

from backend.db import engine, now, rules, sessions, sources, submissions, workspaces
from backend.demo import ACTORS, DEMO_CONTENT, new_id, seed_workspace
from backend.engine import ai_available
from backend.schemas import Contest, Decision, Profile, RevisionInput, Role, Rule, Source, SubmissionInput, Submit
from backend.uploads import extract
from backend.workflow import analyze, contest, detail, metrics, policy, require, save_draft, scoped, transition

app = FastAPI(title="BrandGuard AI", version="1.0.0")
COOKIE = "brandguard_demo"
DIST = Path(__file__).resolve().parents[1] / "dist"


class RoleInput(BaseModel):
    role: Role


def cookie_id(request):
    value = request.cookies.get(COOKIE, "")
    if len(value) != 43:
        return None
    return hashlib.sha256(value.encode()).hexdigest()


def session_for(request: Request):
    session_id = cookie_id(request)
    with engine.connect() as connection:
        actor = connection.execute(select(sessions).where(sessions.c.id == session_id)).one_or_none()
    if actor is None:
        raise HTTPException(401, "Start a live demo workspace to continue.")
    return actor


def session_payload(connection, actor):
    profile = connection.execute(select(workspaces.c.profile).where(
        workspaces.c.id == actor.workspace_id,
    )).scalar_one()
    return dict(role=actor.role, actor=ACTORS[actor.role], profile=profile,
                workspace_id=actor.workspace_id, ai_available=ai_available(), sample=DEMO_CONTENT)


@app.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        connection.execute(select(workspaces.c.id).limit(1))
    return {"status": "ok"}


@app.post("/api/demo", status_code=201)
def start_demo(response: Response):
    token = secrets.token_urlsafe(32)
    token_id = hashlib.sha256(token.encode()).hexdigest()
    with engine.begin() as connection:
        workspace_id = seed_workspace(connection)
        actor = connection.execute(sessions.insert().values(
            id=token_id, workspace_id=workspace_id, role="creator",
        ).returning(*sessions.c)).one()
        payload = session_payload(connection, actor)
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict",
                        secure=os.getenv("SECURE_COOKIES") == "1", max_age=30 * 86400)
    return payload


@app.get("/api/session")
def get_session(actor=Depends(session_for)):
    with engine.connect() as connection:
        return session_payload(connection, actor)


@app.put("/api/demo/role")
def switch_role(data: RoleInput, actor=Depends(session_for)):
    with engine.begin() as connection:
        updated = connection.execute(sessions.update().where(
            sessions.c.id == actor.id,
        ).values(role=data.role).returning(*sessions.c)).one()
        return session_payload(connection, updated)


@app.put("/api/brand")
def edit_brand(data: Profile, actor=Depends(session_for)):
    require(actor, "admin")
    with engine.begin() as connection:
        connection.execute(workspaces.update().where(
            workspaces.c.id == actor.workspace_id,
        ).values(profile=data.model_dump()))
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

from io import BytesIO

import pymupdf
import pytest
from alembic import command
from alembic.config import Config
from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend import db, main, workflow
from backend.demo import DEMO_CONTENT


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///" + str(tmp_path / "test.sqlite"))
    for module in (db, main, workflow):
        monkeypatch.setattr(module, "engine", engine)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("SECURE_COOKIES", "0")
    command.upgrade(Config("alembic.ini"), "head")
    with TestClient(main.app) as client:
        yield client
    engine.dispose()


def start(client):
    result = client.post("/api/demo")
    assert result.status_code == 201
    assert result.json()["profile"]["name"] == "NovaTech"
    return result.json()


def role(client, value):
    assert client.put("/api/demo/role", json={"role": value}).status_code == 200


def submit_copy(client, content=DEMO_CONTENT):
    response = client.post("/api/submissions", json={
        "title": "Launch copy", "content_type": "Advertisement", "platform": "Website", "content": content,
    })
    assert response.status_code == 201, response.text
    return response.json()


def latest(submission):
    return submission["versions"][-1]["reviews"][-1]


def act(client, submission, endpoint, body):
    return client.post(f"/api/submissions/{submission['id']}/{endpoint}",
                       json={"generation": submission["generation"], **body})


def test_novatech_findings_reference_policy_and_fact(client):
    assert client.get("/health").status_code == 200
    assert client.get("/api/knowledge").status_code == 401
    start(client)
    knowledge = client.get("/api/knowledge").json()
    assert "₹499" in next(item["content"] for item in knowledge["sources"] if item["title"] == "NovaTech Product Fact Sheet")
    result = latest(submit_copy(client))
    assert result["mode"] == "Rule-based"
    by_excerpt = {item["original_text"]: item for item in result["findings"]}
    assert set(by_excerpt) == {"magic AI", "100% accurate", "cheapest solution in India", "₹99 per month"}
    assert by_excerpt["₹99 per month"]["evidence_status"] == "CONTRADICTED"
    assert by_excerpt["100% accurate"]["evidence_status"] == "NOT_SUBSTANTIATED"
    for finding in by_excerpt.values():
        assert finding["source_id"] and finding["rule_id"] and finding["suggested_correction"]
        assert finding["source_version"] == finding["rule_version"] == 1
        assert finding["status"] == "OPEN"


def test_claim_uncertainty_and_scoped_price(client):
    start(client)
    result = latest(submit_copy(client, "Best tool in the world. Trial subscription for ₹99 per month. Add seats for ₹49 per month."))
    by_excerpt = {item["original_text"]: item["evidence_status"] for item in result["findings"]}
    assert by_excerpt == {"Best tool in the world": "NOT_SUBSTANTIATED", "₹99 per month": "NEEDS_HUMAN_REVIEW"}


def test_rule_version_deactivation_and_workspace_isolation(client):
    start(client)
    source = client.get("/api/knowledge").json()["sources"][0]
    payload = dict(title="New wording", description="Avoid this terminology.", kind="phrase",
                   category="Terminology", severity="high", pattern="miracle engine", replacement="AI-powered solution",
                   source_id=source["id"])
    assert client.post("/api/rules", json=payload).status_code == 403
    role(client, "admin")
    result = client.post("/api/rules", json=payload)
    assert result.status_code == 201, result.text
    rule = result.json()
    role(client, "creator")
    submission = submit_copy(client, "Try the Miracle Engine now.")
    assert latest(submission)["findings"][0]["rule_id"] == rule["id"]
    role(client, "admin")
    assert client.delete("/api/rules/" + rule["id"]).status_code == 204
    role(client, "creator")
    assert latest(submit_copy(client, "Try the Miracle Engine now."))["findings"] == []
    prior = client.get("/api/submissions/" + submission["id"]).json()
    assert latest(prior)["findings"][0]["rule_version"] == 1
    with TestClient(main.app) as other:
        assert start(other)["workspace_id"] != start(client)["workspace_id"]
        assert other.get("/api/submissions/" + submission["id"]).status_code == 404
        assert other.get("/api/analytics").json()["total"] == 0
        role(other, "admin")
        assert other.post("/api/rules", json=payload).status_code == 404


def test_revision_decisions_and_stale_updates(client):
    start(client)
    first = submit_copy(client)
    role(client, "reviewer")
    assert act(client, first, "decision", {"action": "APPROVED", "comment": "too soon"}).status_code == 409
    role(client, "creator")
    queued = act(client, first, "submit-for-approval", {}).json()
    assert queued["status"] == "PENDING_APPROVAL"
    assert act(client, queued, "decision", {"action": "APPROVED", "comment": "unauthorised"}).status_code == 403
    role(client, "reviewer")
    changes = act(client, queued, "decision", {"action": "CHANGES_REQUESTED", "comment": "Correct the price."}).json()
    assert changes["status"] == "CHANGES_REQUESTED"
    role(client, "creator")
    replacement = {"content": "NovaTech subscription plans start at ₹499 per month."}
    assert act(client, first, "reanalyze", replacement).status_code == 409
    fixed = act(client, changes, "reanalyze", replacement).json()
    assert fixed["versions"][0]["content"] == DEMO_CONTENT
    assert fixed["revision"] == 2 and latest(fixed)["findings"] == []
    queued = act(client, fixed, "submit-for-approval", {}).json()
    role(client, "reviewer")
    approved = act(client, queued, "decision", {"action": "APPROVED", "comment": "Matches the fact sheet."}).json()
    assert approved["status"] == "APPROVED" and approved["actions"][-1]["actor"] == "Jordan Rao"
    role(client, "creator")
    next_revision = act(client, approved, "reanalyze", {"content": "Explore our AI-powered solution."}).json()
    assert next_revision["status"] == "REVIEWED" and next_revision["revision"] == 3
    assert next_revision["actions"][-1]["action"] == "SUPERSEDED"
    assert client.get("/api/analytics").json()["violations"] == 4


def test_file_extraction_and_invalid_input(client):
    start(client)
    assert client.post("/api/extract", files={"file": ("wrong.png", b"image")}).status_code == 415
    assert client.post("/api/extract", files={"file": ("broken.pdf", b"bad")}).status_code == 422
    assert client.post("/api/extract", files={"file": ("big.txt", b"x" * (5 * 1024 * 1024 + 1))}).status_code == 413
    document = Document()
    document.add_paragraph("Approved terminology")
    buffer = BytesIO()
    document.save(buffer)
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((72, 72), "Approved terminology")
        pdf_bytes = pdf.tobytes()
    for filename, payload in [("guide.txt", b"Approved terminology"), ("guide.pdf", pdf_bytes), ("guide.docx", buffer.getvalue())]:
        result = client.post("/api/extract", files={"file": (filename, payload)})
        assert result.status_code == 200 and result.json()["content"] == "Approved terminology"


def test_ai_fallback_after_malformed_response(client, monkeypatch):
    from backend import engine
    monkeypatch.setenv("LLM_CHAT_URL", "https://example.test/chat")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setattr(engine.httpx, "post", lambda *args, **kwargs: engine.httpx.Response(
        200, json={"choices": [{"message": {"content": "invalid"}}]},
        request=engine.httpx.Request("POST", "https://example.test/chat"),
    ))
    start(client)
    result = client.post("/api/submissions", json={
        "title": "Test", "content_type": "Ad", "platform": "Web", "content": DEMO_CONTENT, "use_ai": True,
    })
    assert result.status_code == 201
    assessment = latest(result.json())
    assert assessment["mode"] == "Rule-based" and len(assessment["findings"]) == 4
    assert "unavailable" in assessment["notice"]


def test_saved_draft_analysis_and_finding_contest(client):
    start(client)
    created = client.post("/api/submissions/draft", json={
        "title": "Draft launch copy", "content_type": "Ad", "platform": "Web", "content": DEMO_CONTENT,
    })
    assert created.status_code == 201
    draft = created.json()
    assert draft["status"] == "DRAFT" and draft["versions"][0]["reviews"] == []
    assert act(client, draft, "submit-for-approval", {}).status_code == 409
    reviewed = act(client, draft, "reanalyze", {"content": DEMO_CONTENT}).json()
    assert reviewed["status"] == "REVIEWED" and len(reviewed["versions"]) == 1
    finding = latest(reviewed)["findings"][0]
    result = client.put(
        f"/api/submissions/{reviewed['id']}/findings/{finding['id']}",
        json={"generation": reviewed["generation"], "status": "CONTESTED", "reason": "Verify with the policy owner."},
    )
    assert result.status_code == 200
    assert latest(result.json())["findings"][0]["status"] == "CONTESTED"
    assert result.json()["actions"][-1]["action"] == "FINDING_CONTESTED"

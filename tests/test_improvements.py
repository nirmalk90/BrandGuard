from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from alembic import command
from alembic.config import Config
import cv2
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from backend import db, main
from backend.artwork import visual_review
from backend.wordpress import fingerprint
from test_workflow import act, client, latest, role, start


def picture(fmt="PNG", off_brand=True):
    logo = Image.new("RGB", (100, 70), "white")
    pen = ImageDraw.Draw(logo)
    pen.polygon([(7, 8), (65, 8), (85, 33), (38, 62), (7, 48)], fill="#3DE0C2")
    pen.line([(17, 43), (31, 23), (44, 48), (64, 19)], fill="#132349", width=5)
    canvas = Image.new("RGB", (720, 300), "white")
    canvas.paste(logo, (35, 35))
    if off_brand:
        ImageDraw.Draw(canvas).rectangle([500, 0, 719, 299], fill="#ee1833")
    pixels = np.array(canvas)
    cv2.putText(pixels, "guaranteed results", (25, 215), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (10, 10, 10), 3, cv2.LINE_AA)
    out, ref = BytesIO(), BytesIO()
    Image.fromarray(pixels).save(out, format=fmt)
    logo.save(ref, format="PNG")
    return out.getvalue(), ref.getvalue()


def asset(client, url, name, payload):
    return client.post("/api/" + url, files={"file": (name, payload)})


def review(client, **fields):
    payload = dict(title="Launch", content_type="Advertisement", platform="Web", campaign="Launch")
    response = client.post("/api/submissions", json={**payload, **fields})
    assert response.status_code == 201, response.text
    return response.json()


def test_real_ocr_logo_colour_regions_and_immutable_artwork(client):
    start(client)
    art, logo = picture()
    assert asset(client, "logos", "mark.png", logo).status_code == 403
    role(client, "admin")
    ref = asset(client, "logos", "mark.png", logo)
    assert ref.status_code == 201, ref.text
    role(client, "creator")
    first = asset(client, "artwork", "launch.png", art)
    assert first.status_code == 201, first.text
    key = first.json()["id"]
    submission = review(client, content="100% accurate", artwork_id=key)
    findings = latest(submission)["findings"]
    assert "guaranteed results" in submission["versions"][0]["artwork"]["text"]
    assert any(f["origin"] == "copy" and f["original_text"] == "100% accurate" for f in findings)
    ocr = next(f for f in findings if f["origin"] == "artwork" and f["original_text"] == "guaranteed results")
    assert ocr["regions"] and min(b[1] for b in ocr["regions"]) > .4
    assert any(f["category"] == "Brand colours" and f["regions"][0][0] > .6 for f in findings)
    assert any(f["category"] == "Brand logo" and f["evidence_status"] == "SUPPORTED" and f["regions"] for f in findings)
    queued = act(client, submission, "submit-for-approval", {}).json()
    role(client, "reviewer")
    approved = act(client, queued, "decision", dict(action="APPROVED", comment="Checked artwork.")).json()
    role(client, "creator")
    replacement = asset(client, "artwork", "launch.jpg", picture("JPEG", False)[0]).json()["id"]
    revised = act(client, approved, "reanalyze", dict(content="100% accurate", artwork_id=replacement)).json()
    assert revised["revision"] == 2 and revised["status"] == "REVIEWED"
    assert revised["versions"][0]["artwork"]["id"] == key
    assert revised["actions"][-1]["action"] == "SUPERSEDED"
    assert not any(f["category"] == "Brand colours" for f in latest(revised)["findings"])
    assert review(client, artwork_id=replacement)["versions"][0]["content"] == ""
    with TestClient(main.app) as other:
        start(other)
        assert other.get("/api/assets/"+key).status_code == 404
        assert other.post("/api/submissions", json=dict(content_type="Ad", platform="Web",
            title="Foreign", artwork_id=key)).status_code == 404
    assert asset(client, "artwork", "bad.png", b"bad").status_code == 422
    assert asset(client, "artwork", "bad.svg", art).status_code == 415


def test_approved_and_recoloured_logos_are_localised_in_same_artwork():
    art, logo = picture()
    canvas = Image.open(BytesIO(art))
    variant = np.array(Image.open(BytesIO(logo)))
    variant[np.all(variant == [61, 224, 194], axis=2)] = [220, 30, 50]
    canvas.paste(Image.fromarray(variant), (280, 35))
    buf = BytesIO()
    canvas.save(buf, format="PNG")
    workspace = SimpleNamespace(profile={"primary_color":"#3DE0C2","secondary_color":"#5B8FF9"},
                                palette_version=1, logo_version=2)
    items, _ = visual_review({"image":buf.getvalue()}, [{"id":"reference","image":logo,"name":"mark.png"}], workspace)
    marks = [item for item in items if item.category == "Brand logo"]
    assert any(item.evidence_status == "SUPPORTED" and item.regions[0][0] < .1 for item in marks)
    assert any(item.requires_human_review and .35 < item.regions[0][0] < .45 for item in marks)


def test_campaign_conflicts_comparison_and_exact_evidence(client):
    start(client)
    role(client, "admin")
    knowledge = client.get("/api/knowledge").json()
    spec = dict(title="Mandatory AI phrase", description="Use this exact term.", kind="required",
                category="Terminology", severity="medium", pattern="magic AI", source_id=knowledge["sources"][0]["id"])
    rule = client.post("/api/rules", json=spec).json()
    role(client, "creator")
    first = review(client, content="magic AI")
    rerun = act(client, first, "reanalyze", dict(content="magic AI")).json()
    second = review(client, content="magic AI")
    review(client, content="magic AI", campaign="Separate campaign")
    role(client, "admin")
    assert client.put("/api/rules/"+rule["id"], json={**spec, "pattern": "Approved phrase"}).status_code == 200
    role(client, "creator")
    clean = review(client, content="Approved phrase")
    patterns = client.get("/api/governance", params={"campaign": "Launch"}).json()
    old, new = sorted([p for p in patterns if p["rule_id"] == rule["id"]], key=lambda p:p["version"])
    assert (old["flagged"], old["assessed"], old["conflicts"]) == (2,2,2)
    def evidence(row, flag):
        return client.get("/api/governance/evidence", params={"campaign":"Launch","rule_id":row["rule_id"],
                          "version":row["version"],"flag":flag}).json()["reviews"]
    assert {r["review_id"] for r in evidence(old, "conflict")} == {latest(rerun)["id"], latest(second)["id"]}
    assert (new["flagged"], new["assessed"], new["conflicts"]) == (0,1,0)
    assert evidence(new, "all")[0]["submission_id"] == clean["id"]
    assert not evidence(new, "violation")
    assert client.get("/api/governance", params={"campaign":"Unknown"}).json() == []
    moved = client.put("/api/submissions/"+second["id"]+"/campaign", json={"campaign":"Later", "generation":1})
    assert moved.json()["campaign"] == "Later"


def test_wordpress_exact_snapshot_idempotency_revocation_and_isolation(client):
    start(client)
    role(client, "admin")
    archive = ZipFile(BytesIO(client.get("/api/integrations/wordpress/plugin.zip").content))
    assert set(archive.namelist()) == {"brandguard/brandguard.php", "brandguard/editor.js"}
    token = client.post("/api/integrations/wordpress").json()["key"]
    headers = {"Authorization": "Bearer " + token}
    snapshot = dict(title="Launch", content="<p>magic AI</p>", excerpt="Teaser", slug="launch", featured_media=123)
    path = "/api/wordpress/posts/12"
    def send(s):
        return client.post(path, headers=headers, json={"snapshot":s, "campaign":"Launch"}).json()
    queued = send(snapshot)
    assert queued["status"] == "PENDING_APPROVAL" and send(snapshot) == queued
    role(client, "reviewer")
    submission = client.get("/api/submissions/"+queued["submission_id"]).json()
    assert submission["wordpress"] == snapshot
    assert latest(submission)["findings"][0]["original_text"] == "magic AI"
    approved = act(client, submission, "decision", {"action":"APPROVED","comment":"Ready."}).json()
    get = lambda s: client.get(path, headers=headers, params={"digest":fingerprint(s)}).json()
    assert get(snapshot)["status"] == "APPROVED" and get(snapshot)["comment"] == "Ready."
    for field, value in [("content","<p>magic AI</p> "),("title","Launch!"),("excerpt","Other"),("slug","other"),("featured_media",0)]:
        assert get({**snapshot,field:value})["status"] == "NEEDS_REVIEW"
    changed = send({**snapshot,"content":"<p>magic AI</p> "})
    assert changed["status"] == "PENDING_APPROVAL" and changed["submission_id"] != queued["submission_id"]
    role(client, "creator")
    assert act(client, approved, "reanalyze", {"content":"modified"}).status_code == 409
    with TestClient(main.app) as other:
        start(other)
        role(other, "admin")
        k = other.post("/api/integrations/wordpress").json()["key"]
        assert other.get(path, params={"digest":fingerprint(snapshot)}, headers={"Authorization":"Bearer "+k}).json()["status"] == "NOT_SUBMITTED"
    role(client, "admin")
    assert client.delete("/api/integrations/wordpress").status_code == 204
    assert client.get(path, params={"digest":fingerprint(snapshot)}, headers=headers).status_code == 401


def test_team_sessions_have_fixed_roles_and_named_decisions(client, monkeypatch):
    workspace = start(client)["workspace_id"]
    monkeypatch.setenv("BRANDGUARD_MODE","team")
    assert client.post("/api/demo").status_code == 403
    assert client.get("/api/session").status_code == 401
    key = "T"*43
    with db.engine.begin() as conn:
        conn.execute(db.members.insert().values(id=sha256(key.encode()).hexdigest(), workspace_id=workspace,
                                               role="creator", name="Team Creator"))
    login = client.post("/api/login", json={"key":key}).json()
    assert login["actor"] == "Team Creator" and not login["demo"]
    assert client.put("/api/demo/role", json={"role":"admin"}).status_code == 403
    assert client.post("/api/integrations/wordpress").status_code == 403
    assert review(client, content="For teams")["creator"] == "Team Creator"
    assert client.post("/api/logout").status_code == 204
    assert client.get("/api/session").status_code == 401


def test_upgrade_preserves_preexisting_history_and_unknown_coverage(client):
    start(client)
    original = review(client, content="magic AI")
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "0001")
    command.upgrade(cfg, "head")
    command.check(cfg)
    restored = client.get("/api/submissions/"+original["id"]).json()
    assert restored["campaign"] == "Unassigned"
    assert latest(restored)["id"] == latest(original)["id"]
    legacy = client.get("/api/governance?campaign=Unassigned").json()
    assert len(legacy) == 1 and legacy[0]["assessed"] is None and legacy[0]["flagged"] == 1


def test_concurrent_wordpress_retries_create_one_review(client):
    start(client)
    role(client, "admin")
    key = client.post("/api/integrations/wordpress").json()["key"]
    def send(_):
        with TestClient(main.app) as publisher:
            return publisher.post("/api/wordpress/posts/99", headers={"Authorization":"Bearer "+key},
                json={"snapshot":dict(title="Launch",content="<p>magic AI</p>",excerpt="",slug="",featured_media=0)})
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(send, range(4)))
    assert all(result.status_code == 200 for result in results)
    assert len({result.json()["submission_id"] for result in results}) == 1
    assert len(client.get("/api/submissions").json()) == 1

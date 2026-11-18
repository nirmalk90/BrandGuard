from collections import Counter
from hashlib import sha256

from fastapi import HTTPException
from sqlalchemy import select

from backend import artwork
from backend.db import actions, assets, engine, findings, now, posts, reviews, rules, sources, submissions, versions, workspaces
from backend.demo import ACTORS, new_id
from backend.engine import applicable, review


def scoped(connection, table, actor, item_id):
    record = connection.execute(select(table).where(
        table.c.id == item_id, table.c.workspace_id == actor.workspace_id,
    )).mappings().one_or_none()
    if record is None:
        raise HTTPException(404, "This item is unavailable in your workspace.")
    return dict(record)


def require(actor, *roles):
    if actor.role not in roles:
        raise HTTPException(403, "Your workspace role cannot perform this action.")


def advance(connection, record, generation, status, revision=None):
    changed = connection.execute(submissions.update().where(
        submissions.c.id == record["id"],
        submissions.c.workspace_id == record["workspace_id"],
        submissions.c.generation == generation,
    ).values(status=status, generation=generation + 1,
             revision=revision or record["revision"], updated_at=now()))
    if changed.rowcount != 1:
        raise HTTPException(409, "This submission changed. Reload it and try again.")


def current_version(connection, record):
    return connection.execute(select(versions).where(
        versions.c.submission_id == record["id"], versions.c.number == record["revision"],
    )).mappings().one()


def policy(connection, workspace_id):
    return list(connection.execute(select(
        rules, sources.c.title.label("source_title"), sources.c.content.label("source_content"),
        sources.c.version.label("source_version"),
    ).join(sources).where(rules.c.workspace_id == workspace_id,
                         sources.c.workspace_id == workspace_id).order_by(rules.c.created_at, rules.c.id)).mappings())


def rule_snapshot(policy_rows):
    return [dict(id=r["id"], title=r["spec"]["title"], version=r["version"]) for r in applicable(policy_rows)]


def save_review(connection, version_id, result, snapshot):
    assessment, mode, checked, notice = result
    review_id = new_id()
    connection.execute(reviews.insert().values(
        id=review_id, version_id=version_id, mode=mode, rules_checked=checked, notice=notice,
        rules_snapshot=snapshot,
    ))
    if assessment:
        connection.execute(findings.insert(), [
            dict(id=new_id(), review_id=review_id, rule_id=item.rule_id,
                 evidence=item.model_dump(), status="OPEN", reason=None)
            for item in assessment
        ])


def detail(connection, actor, submission_id):
    record = scoped(connection, submissions, actor, submission_id)
    revision_list = []
    for version in connection.execute(select(versions).where(
        versions.c.submission_id == submission_id,
    ).order_by(versions.c.number)).mappings():
        review_list = []
        for assessment in connection.execute(select(reviews).where(
            reviews.c.version_id == version.id,
        ).order_by(reviews.c.created_at, reviews.c.id)).mappings():
            items = [
                {**finding.evidence, "id": finding.id, "status": finding.status, "reason": finding.reason}
                for finding in connection.execute(select(findings).where(
                    findings.c.review_id == assessment.id,
                ).order_by(findings.c.id)).mappings()
            ]
            review_list.append({**assessment, "findings": items})
        image_info = None
        if version.artwork_id:
            image = connection.execute(select(*artwork.PUBLIC, assets.c.lines).where(
                assets.c.id == version.artwork_id, assets.c.workspace_id == actor.workspace_id)).mappings().one()
            image_info = {c.name: image[c.name] for c in artwork.PUBLIC}
            image_info["text"] = "\n".join(" ".join(w["text"] for w in line) for line in image.lines)
        revision_list.append({**version, "artwork": image_info, "reviews": review_list})
    decisions = list(connection.execute(select(actions).where(
        actions.c.submission_id == submission_id,
    ).order_by(actions.c.created_at, actions.c.id)).mappings())
    wordpress = connection.execute(select(posts.c.snapshot).where(
        posts.c.submission_id == submission_id)).scalar_one_or_none()
    return {**record, "versions": revision_list, "actions": decisions, "wordpress": wordpress}


def attached(connection, actor, asset_id):
    if asset_id:
        asset = scoped(connection, assets, actor, asset_id)
        if asset["kind"] != "artwork":
            raise HTTPException(422, "Choose a marketing artwork upload.")
        return asset


def actor_name(actor):
    return getattr(actor, "name", None) or ACTORS[actor.role]


def analyze(actor, data, submission_id=None):
    require(actor, "creator")
    content_hash = sha256(data.content.encode()).hexdigest()
    with engine.connect() as connection:
        applicable_policy = policy(connection, actor.workspace_id)
        asset_id = data.artwork_id
        if submission_id:
            existing = scoped(connection, submissions, actor, submission_id)
            if connection.execute(select(posts.c.id).where(posts.c.submission_id == submission_id)).first():
                raise HTTPException(409, "Send changed WordPress drafts from the post editor.")
            if existing["generation"] != data.generation:
                raise HTTPException(409, "This submission changed. Reload it and try again.")
            previous = current_version(connection, existing)
            if "artwork_id" not in data.model_fields_set:
                asset_id = previous.artwork_id
            same_content = previous.content_hash == content_hash and previous.artwork_id == asset_id
            if same_content and existing["status"] not in {"DRAFT", "REVIEWED"}:
                raise HTTPException(409, "Edit the content to start a new revision.")
        asset = attached(connection, actor, asset_id)
        if asset:
            workspace = connection.execute(select(workspaces).where(
                workspaces.c.id == actor.workspace_id).with_for_update(read=True)).one()
            refs = artwork.logos(connection, actor, include_pixels=True)
    words, spans = artwork.text_evidence(asset["lines"]) if asset else ("", [])
    items, mode, checked, notice = review(data.content, applicable_policy, data.use_ai, words, spans)
    snapshot = rule_snapshot(applicable_policy)
    if asset:
        with artwork.processing_slot():
            visual_items, checks = artwork.visual_review(asset, refs, workspace)
        items.extend(visual_items)
        snapshot.extend(checks)
        notes = [notice] if notice else []
        if not words:
            notes.append("OCR found no readable text. Inspect the artwork manually.")
        if not refs:
            notes.append("Add an approved logo in Settings to enable logo comparison.")
        notice = " ".join(notes) or None
    result = items, mode, len(snapshot), notice
    with engine.begin() as connection:
        if submission_id:
            revision = existing["revision"] if same_content else existing["revision"] + 1
            advance(connection, existing, data.generation, "REVIEWED", revision)
            version_id = previous.id if same_content else new_id()
            if not same_content and existing["status"] in {"APPROVED", "PENDING_APPROVAL"}:
                log_action(connection, existing["id"], previous.id, actor,
                           "SUPERSEDED", "A new revision superseded this approval state.")
        else:
            submission_id, version_id, revision = new_id(), new_id(), 1
            connection.execute(submissions.insert().values(
                id=submission_id, workspace_id=actor.workspace_id, title=data.title,
                content_type=data.content_type, platform=data.platform, status="REVIEWED",
                creator=actor_name(actor), campaign=data.campaign, revision=1, generation=1,
            ))
            same_content = False
        if not same_content:
            connection.execute(versions.insert().values(
                id=version_id, submission_id=submission_id, number=revision,
                content=data.content, content_hash=content_hash, artwork_id=asset_id,
            ))
        save_review(connection, version_id, result, snapshot)
        return detail(connection, actor, submission_id)


def save_draft(actor, data):
    require(actor, "creator")
    submission_id = new_id()
    with engine.begin() as connection:
        attached(connection, actor, data.artwork_id)
        connection.execute(submissions.insert().values(
            id=submission_id, workspace_id=actor.workspace_id, title=data.title,
            content_type=data.content_type, platform=data.platform, status="DRAFT",
            creator=actor_name(actor), campaign=data.campaign, revision=1, generation=1,
        ))
        connection.execute(versions.insert().values(
            id=new_id(), submission_id=submission_id, number=1,
            content=data.content, content_hash=sha256(data.content.encode()).hexdigest(), artwork_id=data.artwork_id,
        ))
        return detail(connection, actor, submission_id)


def log_action(connection, submission_id, version_id, actor, action, comment):
    connection.execute(actions.insert().values(
        id=new_id(), submission_id=submission_id, version_id=version_id,
        actor=actor_name(actor), action=action, comment=comment,
    ))


def transition(actor, submission_id, generation, status, comment):
    required_role, required_status = (
        ("creator", "REVIEWED") if status == "PENDING_APPROVAL"
        else ("reviewer", "PENDING_APPROVAL")
    )
    require(actor, required_role)
    with engine.begin() as connection:
        record = scoped(connection, submissions, actor, submission_id)
        if record["status"] != required_status:
            raise HTTPException(409, "This action is unavailable for the current status.")
        version = current_version(connection, record)
        advance(connection, record, generation, status)
        log_action(connection, submission_id, version.id, actor, status, comment)
        return detail(connection, actor, submission_id)


def contest(actor, submission_id, finding_id, data):
    require(actor, "creator")
    with engine.begin() as connection:
        record = scoped(connection, submissions, actor, submission_id)
        if record["status"] != "REVIEWED":
            raise HTTPException(409, "Findings can be updated before requesting approval.")
        version = current_version(connection, record)
        latest = connection.execute(select(reviews.c.id).where(
            reviews.c.version_id == version.id,
        ).order_by(reviews.c.created_at.desc(), reviews.c.id.desc()).limit(1)).scalar_one()
        advance(connection, record, data.generation, record["status"])
        changed = connection.execute(findings.update().where(
            findings.c.id == finding_id, findings.c.review_id == latest,
        ).values(status=data.status, reason=data.reason))
        if changed.rowcount != 1:
            raise HTTPException(404, "This finding is unavailable in the current review.")
        log_action(connection, submission_id, version.id, actor, "FINDING_" + data.status,
                   f"{finding_id}: {data.reason}")
        return detail(connection, actor, submission_id)


def metrics(connection, actor):
    records = connection.execute(select(submissions.c.status).where(
        submissions.c.workspace_id == actor.workspace_id,
    )).scalars().all()
    review_scope = reviews.join(versions).join(submissions)
    review_dates = connection.execute(select(reviews.c.created_at).select_from(review_scope).where(
        submissions.c.workspace_id == actor.workspace_id,
    )).scalars()
    issues = connection.execute(select(findings.c.evidence).select_from(
        review_scope.join(findings),
    ).where(submissions.c.workspace_id == actor.workspace_id)).scalars()
    categories, severity, rule_counts = Counter(), Counter(), Counter()
    for item in issues:
        if item["evidence_status"] == "SUPPORTED":
            continue
        categories[item["category"]] += 1
        severity[item["severity"]] += 1
        if item["rule_title"]:
            rule_counts[item["rule_title"]] += 1
    return {
        "total": len(records), "statuses": dict(Counter(records)),
        "violations": sum(categories.values()), "categories": dict(categories),
        "severity": dict(severity), "rules": dict(rule_counts.most_common(8)),
        "trends": dict(sorted(Counter(value.date().isoformat() for value in review_dates).items())),
    }

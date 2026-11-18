from collections import defaultdict

from sqlalchemy import select

from backend.db import findings, reviews, submissions, versions


def patterns(conn, actor, campaign, *, rule_key=None):
    scope = submissions.join(versions).join(reviews)
    where = (submissions.c.workspace_id == actor.workspace_id, submissions.c.campaign == campaign)
    query = select(submissions.c.id.label("submission_id"), submissions.c.title,
                   versions.c.number, versions.c.id.label("version_id"), reviews.c.id.label("review_id"),
                   reviews.c.created_at, reviews.c.rules_snapshot).select_from(scope).where(*where).order_by(reviews.c.created_at, reviews.c.id)
    evidence = defaultdict(list)
    for row in conn.execute(select(findings.c.review_id, findings.c.evidence, findings.c.status)
                            .select_from(scope.join(findings)).where(*where)):
        item = row.evidence
        key = (item.get("policy_key") or item.get("rule_id"), item.get("rule_version"))
        if all(key) and (rule_key is None or key == rule_key):
            evidence[row.review_id].append((key, item["rule_title"], item.get("conflict"),
                                            item["evidence_status"], row.status))

    # Keep the last evaluation of each rule version on a given draft revision.
    # Rechecking the same artwork or copy cannot manufacture recurrence.
    buckets = defaultdict(dict)
    titles = {}
    for row in conn.execute(query):
        checks = {(r["id"], r["version"]): r["title"] for r in row.rules_snapshot or []
                  if rule_key is None or (r["id"], r["version"]) == rule_key}
        flags = defaultdict(set)
        for key, title, conflict, finding_status, status in evidence.pop(row.review_id, []):
            checks[key] = title
            if conflict:
                flags[key].add("conflict")
            if status in ("CONTESTED", "DISMISSED"):
                flags[key].add("disputed")
            if finding_status != "SUPPORTED" and status != "DISMISSED":
                flags[key].add("flagged")
            if finding_status == "CONTRADICTED" and status != "DISMISSED":
                flags[key].add("violation")
        for key, title in checks.items():
            titles[key] = title
            entry = dict(flags=sorted(flags[key]), measured=row.rules_snapshot is not None)
            if rule_key:
                entry.update(review_id=row.review_id, submission_id=row.submission_id,
                             title=row.title, revision=row.number, created_at=row.created_at)
            buckets[key][row.version_id] = entry
    if rule_key:
        return sorted(buckets[rule_key].values(), key=lambda link: (link["created_at"], link["review_id"]), reverse=True)
    result = []
    for (rule_id, version), revisions in buckets.items():
        links = list(revisions.values())
        flagged = sum("flagged" in link["flags"] for link in links)
        measured = all(link["measured"] for link in links)
        result.append(dict(rule_id=rule_id, version=version, title=titles[rule_id, version],
                           assessed=len(links) if measured else None, flagged=flagged,
                           violations=sum("violation" in link["flags"] for link in links),
                           conflicts=sum("conflict" in link["flags"] for link in links),
                           disputed=sum("disputed" in link["flags"] for link in links)))
    return sorted(result, key=lambda r: (r["title"].casefold(), r["rule_id"], -r["version"]))

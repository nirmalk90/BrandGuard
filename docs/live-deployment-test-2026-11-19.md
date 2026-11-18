# BrandGuard live deployment test

Date: 19 November 2026 (IST)
Target: https://brandguard-ai-pt15.onrender.com/

**Result: the tested judge workflows pass on the public deployment.** Demo access is enabled. No application-code changes were required. This is a functional test of the current running release, not certification of production readiness.

## Scope and method

Used fresh, isolated NovaTech demo workspaces and synthetic test copy, documents and artwork. Exercised the deployed service with Playwright/Chromium and HTTP requests. All created reviews, policies and integration keys belonged to test workspaces. The temporary WordPress connection key was revoked after its checks. No service restart, deployment, database migration or infrastructure change was performed.

## Results

| Check | Result | Evidence |
| --- | --- | --- |
| Public entry, health, access and API schema | Pass | HTTP 200; demo enabled; API version 2.0.0. |
| Existing Playwright suite against live URL | 3 passed, 1 skipped | Artwork/history scenario 17.4 s; complete judge workflow 12.0 s; mobile/rule scenario 6.5 s. Real WordPress editor scenario skipped. Suite duration 39.2 s. |
| Session and access checks | Pass | Anonymous knowledge access rejected; new workspace has zero submissions; session cookie has Secure, HttpOnly and SameSite=Strict. |
| Document imports and input validation | Pass | TXT, PDF and DOCX extraction; empty copy, corrupt PDF/PNG, unsupported extension and over-5-MB document rejected. |
| Permissions, history and isolation | Pass | Creator cannot approve; reviewer cannot create; stale generation rejected; change request, revision, approval and superseding edit work; unrelated workspace cannot read the review. |
| PNG and JPG artwork | Pass | Real OCR found embedded text; copy and image findings coexist; approved logo match and off-brand colour regions include coordinates. |
| Campaign governance API | Pass | Distinct affected revisions counted once despite reanalysis; other campaign excluded; rule versions and exact assessment IDs preserved. |
| WordPress API and plugin download | Pass | Valid ZIP, snapshot submission, identical retry reuse, approval lookup, change detection for all five fingerprinted fields and key revocation. |
| Additional live governance browser exercise | Pass | Recurring-violation/conflict filters, evidence links, version rate from 100% to 0% (-100 pp), campaign isolation and deduplication. |
| Browser reconnection | Pass | A fresh browser context carrying the same session retrieved the exact saved assessment. |
| Visual inspection | Pass for inspected screens | Welcome, desktop dashboard, populated campaign table and 390 px mobile dashboard inspected. Mobile workflow test found no horizontal document overflow. |
| Runtime errors in additional browser exercise | None observed | No JavaScript exceptions, HTTP 5xx responses or failed requests captured in that exercise. This is not a statement about all server logs. |

Six additional API scenario groups passed. These groups are separate from the earlier local 14-test Python suite; they should not be reported as 14 tests run on production.

## Observed timings

The initial warm HTTP requests took approximately 0.28-0.62 seconds. Synthetic artwork upload plus review took 5.09 seconds for PNG and 5.42 seconds for JPEG, including a role-switch request. These are individual observations from this run, not latency percentiles, cold-start measurements or load-test results.

## Outstanding verification

- The PHP plugin and actual WordPress block editor were not exercised. No connected WordPress URL and test credentials were supplied. Backend/API success does not establish full editor integration success.
- Storage across a Render restart, redeployment or free-service spin-down was not tested. The public API does not establish whether the deployment uses persistent PostgreSQL or ephemeral SQLite.
- Private team-member provisioning/sign-in was not tested against the live deployment; this run used demo sessions and demo role enforcement.
- Optional external model inference, backup restoration, cold starts, sustained load, a full security audit and broad OCR accuracy benchmarking remain outside this run.
- Original Round 2 scope omissions (layout/accessibility checks, design handoffs, complete policy edit audits and direct cross-campaign comparison) remain unchanged.

## Judge instructions

Open the live URL and click **Try Live Demo**. Review the prefilled copy, revise and re-run, submit for approval, select the Reviewer demo role, record a decision and reopen it after refresh. Each fresh browser session receives its own sample workspace. To test visual review, use the Admin demo role to upload an approved logo, then Creator to attach artwork. Campaign recurrence needs multiple distinct reviewed revisions assigned to the same campaign.

## Evidence files

- `output/deployment-test-2026-11-19/api-results.json`
- `output/deployment-test-2026-11-19/browser-results.json`
- `output/deployment-test-2026-11-19/welcome.png`
- `output/deployment-test-2026-11-19/overview.png`
- `output/deployment-test-2026-11-19/governance.png`
- `output/deployment-test-2026-11-19/mobile.png`

Reproduction of the existing browser suite from PowerShell:

```powershell
$env:BRANDGUARD_TEST_URL='https://brandguard-ai-pt15.onrender.com'
npm test -- --workers=1 --timeout=90000
```

These tests create isolated sample workspaces and review records on the target service.

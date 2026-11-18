# BrandGuard AI: Round 3 readiness audit

Audit date: 18 November 2026 (IST)

## Live deployment verification completed 19 November 2026

The public application at https://brandguard-ai-pt15.onrender.com/ now has demo access enabled and passed the three existing browser scenarios, six additional API scenario groups and an additional governance browser exercise. The real WordPress editor test remains skipped. Persistence across infrastructure restart/redeploy is still unverified. See [the live deployment test report](live-deployment-test-2026-11-19.md) for current evidence and limitations. Earlier statements below about the absence of a public URL, inaccessible judge entry or only local verification are historical and superseded by this run.

## Final organizer instructions received 19 November 2026

The latest announcement supplied by the user supersedes the earlier submission instructions: **one submission for the whole team, made by the team leader; members do not submit separately.** Submit at https://forms.gle/FxhT5Z1NupvGTGSw6 by **21 November 2026 at 11:59 PM IST**, with no late window or extension. The web reader could not open the form, so its individual fields and upload restrictions have not been verified.

All eight deliverables are required: final working project link, final source repository, final product PDF, complete feature list, technical architecture/implementation summary, improvements completed after Round 2 (including the exact three committed), testing details, and product roadmap/future development plan.

Scoring: completeness 25, three promised improvements 20, reliability 20, usability/real-world fit 20, documentation/roadmap 15. Judges use the product independently. Test invalid inputs, empty states, refresh and repeated actions, and verify clean-checkout setup from the README. No social posts or video demo are required.

The actual Round 2 submission determines the commitment baseline. The narrower descriptions supplied later match the tested implementation more closely, but do not themselves establish what was submitted. If the broader PDF was the submitted version, describe genuinely impossible commitments and the reasons in the final PDF, as the latest announcement requires. The implementation findings below reflect the 18 November audit, not a new deployment verification.

## Updated assessment against the user's clarified descriptions

The user subsequently defined the three improvements as artwork OCR/logo/colour review, a WordPress editor review integration, and campaign-level rule recurrence/conflict tracking. Against this exact scope:

| Improvement | Verification status |
| --- | --- |
| 1. Multimodal Brand Verification | Pass in local API and browser checks. PNG and JPEG uploads, real English OCR, copy plus artwork findings, logo matching and recoloured-logo warnings, palette regions, and highlighted evidence are exercised. Matching remains heuristic; difficult artwork requires human inspection. |
| 2. Publishing and Collaboration Integration | Backend checks pass: sending a snapshot creates a queued review, approval is returned for that snapshot, changes to any fingerprinted field require review, and retries/revocation/isolation work. The PHP plugin and editor panel are implemented, but the real WordPress browser scenario is still skipped because no connected test site and reviewer credentials are configured. Full integration correctness is not yet verified. |
| 3. Advanced Governance Intelligence | Pass in local API and browser checks. Recurring violations, repeated conflicts, campaign isolation, deduplication, version comparisons and links to the precise assessment work. An additional browser exercise confirmed two affected revisions count as two despite repeat analysis, the rule's rate changes from 100% in v1 to 0% in v2 (-100 percentage points), both filters show the appropriate evidence, and an evidence link opens the exact reviewed assessment. Rates measure observed findings, not proof that a policy change caused an improvement. |

Fresh checks for this follow-up: seven improvement tests passed, the production build and TypeScript check passed, and the existing browser suite had three passes and one skipped WordPress test. The additional governance browser exercise passed after correcting its locator for the campaign dropdown; no application changes were required.

Layout/accessibility checks, design-tool handoffs, complete policy edit audits and direct cross-campaign comparisons are outside these clarified descriptions. The original-proposal comparison below is retained for traceability; those omissions should not be interpreted as failures of the narrower descriptions. If the earlier proposals were submitted to the organizers, explain this scope change in the final report.

## Original-proposal and submission-package assessment

**Verdict against the original PDF: not ready for final submission.** The local core workflow passes the available checks, and substantial work exists in each proposed improvement area. The broader original promises are only partially delivered, the Round 3 changes are unpublished, and the submission package is incomplete.

This is an assessment of the current working tree, not a final project report. Application code and existing submission documents were not changed during this audit.

## Checks actually performed

| Check | Result | What it establishes |
| --- | --- | --- |
| `.venv\Scripts\python -m pytest -q` | 14 passed | SQLite API workflow, policy evidence, permissions, isolation, revisions, real OCR, logo/colour regions, campaign recurrence/conflicts, WordPress API snapshots/retries/revocation, fixed-role sessions and migration preservation. |
| `npm run build` | Passed | TypeScript validation and production Vite build. |
| `npm test` | 3 passed; 1 skipped | Chromium judge journey, mobile navigation/rule creation, artwork evidence and links back to historical assessments. |
| WordPress browser scenario | Skipped | A connected disposable WordPress site and reviewer credentials were not configured. Backend API tests do not execute the WordPress PHP plugin or real block-editor interaction. |
| `.venv\Scripts\python -m pip check` | Passed | Installed Python dependency compatibility. |
| Local browser inspection | Overview and campaign empty state inspected | Desktop presentation is coherent. This was a limited visual inspection, not a complete usability or accessibility audit. |
| Existing PDF | Text inspected; proposal page rendered and inspected | The only supplied PDF is still a three-page Round 2 report. |
| Remote repository | Public; remote HEAD equals `1225ce5ec58421e84d5d0e20a80a03f973e61f78` | GitHub still points to the 13 November Round 2-era commit. The Round 3 additions are local modifications and untracked files. |

The API run used SQLite; the current Round 3 code was not rerun against PostgreSQL. Docker and a PHP/WordPress runtime were not available on PATH. No public deployment URL was found in the repository or GitHub homepage metadata, so production availability was not verified. This does not prove that no deployment exists. Live optional LLM inference was not verified; the app has a supported rule-based mode and a tested malformed-provider fallback.

## Delivery against the three promises

The baseline is the Round 3 proposals in the original Round 2 PDF and Markdown report. The PDF specifically promises logo/layout/accessibility checks; CMS/design workflows; and cross-campaign analysis, policy audits and recurring rule conflicts.

| Promised area | Implemented and supported by evidence | Remaining gap | Assessment |
| --- | --- | --- | --- |
| Multimodal Brand Verification | PNG/JPEG intake, local English OCR, checks of extracted text, approved-logo comparison, palette-region findings, coordinates, versioned visual references and revision-bound artwork. | No implemented layout comparison rules or visual accessibility checks were found. Finding a logo's coordinates is not a check against required placement, margins or a reference layout. Palette matching is not a text contrast check. | Partial |
| Publishing and Collaboration Integrations | Downloadable WordPress plugin, server-side connection key, exact editor snapshots, review decisions, changed-draft invalidation, revocation and named team sessions. | Real WordPress integration remains unverified. No design-tool integration or distinct design-handoff workflow was found. The CMS panel is advisory and does not block WordPress publishing; describe it accurately. | Partial |
| Advanced Governance Intelligence | Campaign assignment, rule-version coverage/rates, percentage-point changes, deduplication per revision, recurring conflicts and evidence links. | The view and API select one campaign at a time; no direct cross-campaign comparison was found. Rule updates overwrite the stored rule specification while incrementing its version. Assessment snapshots and finding excerpts preserve some evidence, but a complete policy edit audit with old/new specifications, editor and time is absent. | Partial |

Relevant implementation locations: `backend/artwork.py:217`, `backend/wordpress.py:99`, `wordpress/brandguard/`, `backend/governance.py:8`, `frontend/Governance.tsx:69`, `backend/main.py:207` and `backend/main.py:302`.

## Prioritized blockers

1. **Deliver the remaining promised capabilities or explain necessary scope changes precisely.** Highest-risk omissions are layout and visual accessibility checks. Define demonstrable acceptance cases for these, the design handoff, policy audit and cross-campaign comparison. An explanation of a changed plan should not claim that an omitted promise was completed.
2. **Publish the final source.** Commit and push all intended code, the `0002` migration, WordPress plugin, frontend assets and tests. A judge cloning GitHub today will not receive the Round 3 implementation. Verify installation and startup from a clean checkout of the exact submitted commit.
3. **Provide and verify judge access.** Supply a working project URL or the organizer-allowed reliable executable. Check the exact release in a fresh browser, including persistence after reload and restart. Docker and Render default to `BRANDGUARD_MODE=team`, which requires a provisioned workspace and access keys; do not assume the anonymous demo will be available. Either configure an isolated demo deliberately or deliver suitable judge access and instructions.
4. **Complete the integration verification.** Connect a disposable real WordPress site and run the existing browser scenario through submission, approval and changed-markup invalidation. If PostgreSQL/Docker is the submitted deployment, validate migration and the core flow there as well.
5. **Prepare the Round 3 submission package.** The existing PDF and `docs/build_report.py` still produce Round 2 material. `CHECKLIST.md` is also a Round 2 checklist. Add the final project/repository links, the completed-improvements matrix, technical implementation, actual testing results, known limitations, changes from the original plan and each member's real contribution. Include significant development AI tools and reused components where applicable under the event rules.

## Submission requirements and administrative status

| Requirement | Current evidence |
| --- | --- |
| Final working project link | Not supplied in the workspace; not verified. |
| Source-code repository | Public repository exists at https://github.com/nirmalk90/BrandGuard; final changes are not published. |
| Updated project PDF | Missing; only `output/pdf/BrandGuard-AI-Round-2.pdf` exists. |
| Completed-improvements list | Not present as a final submission document. The README describes implemented features; this audit identifies outstanding scope. |
| Technical details | README is substantially updated; incorporate accurate final details into the submission format. |
| Testing notes | Current results are recorded above; previous Round 2 results are not proof of Round 3 production verification. |
| Complete feature list | Required by the final announcement; consolidate into the final package. |
| Product roadmap and future development plan | Required by the final announcement; prepare for the final package. |
| Team-member contributions | Still pending in the historical report; actual individual credits are required. |
| Confirmation form and participation payment | Cannot be established from this repository. Check the leader's confirmation receipt separately. |
| Final submission format/link | https://forms.gle/FxhT5Z1NupvGTGSw6 supplied on 19 November; form fields and upload restrictions unverified. |

The final window is **18 November 2026 at 11:59 PM IST through 21 November 2026 at 11:59 PM IST**. The latest organizer announcement says **the team leader submits once for the whole team**. This supersedes the earlier event-page instruction for separate participant entries.

Sources: https://wecodecoders.in/events/codenova-india, the supplied finalist invitation, `docs/round-2-report.md`, and `output/pdf/BrandGuard-AI-Round-2.pdf`. The confirmation page was not accessible through the web reader, and no registration/payment status was inferred.

## Final release checklist

- [ ] Demonstrate each promised improvement or document each precise scope change.
- [ ] Run the real WordPress browser scenario successfully.
- [ ] Verify the final deployment's database migration and judge journey.
- [ ] Commit and push all final source and verify a clean checkout.
- [ ] Publish the exact tested release and confirm judge access.
- [ ] Generate the updated Round 3 PDF using the organizer's format.
- [ ] Include links, improvements, technical details, testing evidence, limitations, disclosures and individual contributions.
- [ ] Include the complete feature list and product roadmap/future development plan.
- [ ] Confirm the team reservation/payment receipt and have the team leader submit the complete package once before the deadline.

No deployment, payment, commit or push was performed during this assessment.

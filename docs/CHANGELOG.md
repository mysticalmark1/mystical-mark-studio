# Changelog

## 1.1.1 — 2026-11-01

- Fix monthly Work-task creation failing when combined registers and assessments exceed 750,000 characters. Manual handoffs now preserve all selected text in one complete task without that aggregate cap.
- Keep the direct API safeguard separate, with instructions to switch to Work rather than split the review.
- Add regression coverage for four registers plus four assessments above the old cap, downloaded packet contents, private-source consent and API-mode handling.
- No database/schema, credentials, private-profile or HTTPS changes.
- Update SSH GitHub publishing, rsync and release-tag instructions.


## 1.1.0 — 2026-10-15

- Release original code, docs and prompt templates under AGPL-3.0-or-later; add full license, notices and visible license/source links.
- Remove original personal request, embedded description, creator-specific brand instructions and private content bank from public source. New planners start empty.
- Migrate legacy description, brand/thumbnail instructions, register/assessment prompts and timezone into private database settings. Existing planner, uploads, drafts/revisions, task history, metrics and publishing records remain unchanged.
- Add private profile editor; generation and description import read private settings.
- Add portable foreground launcher and timezone dependency; manual LAN and restore modes for non-systemd installations.
- Harden Linux updates with private snapshots, custom data-path recovery, source-manifest copying, unit validation, readiness check and code/unit rollback.
- Keep database schema 1 and existing LAN/Caddy settings and CA untouched.
- Expand installation, workflows, certificate, upgrade, publishing and contributor documentation; add regression tests and CI configuration.

## 1.0.0 — private release

Initial single-user creator workspace. Subsequent hotfix corrected systemd scalar-path quoting. Private source references from that release are not distributed in 1.1.0.

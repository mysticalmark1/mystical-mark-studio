# Validation — Studio 1.1.1

Verified 2026-11-01: all 47 Python tests passed on Linux/Python 3.12. New regression coverage prepares one monthly task with four registers and four assessments above 750,000 combined characters, downloads TASK.md, and checks exact full text, single occurrence and selection order for every source. Also checks persisted task reopening, private-source consent, and switching from the API safeguard to a complete Work handoff. No external AI requests or social posts were made. No database or installer changes were needed for this patch. Receiving-service file/model limits are independent of this fix.

The earlier verification record and platform limitations follow.

# Validation — Studio 1.1.0

Release verification: 2026-10-15. This records checks actually performed, not a claim of deployment on every platform.

## Passed

- 43 Python tests: original application coverage plus private-profile editing/migration, authentication/CSRF, source archive exclusions, manifest path safety, credential loading, private snapshots, data-path recovery, successful update transaction and injected startup failure rollback.
- Regression test against the actual original v1 source in an isolated synthetic installation: all 80 original ideas retained, including edited status/rating; saved files, draft revisions, jobs and model preferences retained; login configuration, credentials and Caddyfile unchanged. Migrated description and register/assessment templates matched the originals exactly. No real user database was accessed.
- The installer transaction tests simulate systemd/dependency installation; they do not claim a real systemd user service was installed in this environment.
- Generated service unit accepted by systemd-analyze verify, including a data path containing spaces. The earlier scalar-path quoting bug remains fixed.
- JavaScript syntax check with Node; Python dependency consistency check.
- Live Waitress startup, login, state retrieval, private-profile save and unauthenticated source download. A saved private sentinel was absent from every source archive member.

## Deployment limits

- Linux/Python 3.12 backend exercised. Windows/macOS foreground commands and native certificate trust have not been run on those operating systems. CI configuration is provided for all three systems, but remote GitHub CI has not yet run.
- This release's automated browser check could not run: the browser executable was unavailable and its download failed. No new visual/mobile browser pass is claimed. The private-profile API is covered by tests.
- No live paid AI calls, X/Threads posts or real-account connections were made. External provider entitlement, models and permissions require operator verification.
- No device firewall/VPN/certificate changes were made. Existing gateway and CA are left untouched by upgrade.
- Public archive checks exclude original personal request/content bank, runtime databases, credentials, certificates, private client uploads, caches, installed dependencies and Git history. Project branding remains. Third-party authors' required notices are retained.

No formal security audit or legal certification is claimed. Read LICENSE, THIRD_PARTY_NOTICES.md and SECURITY.md for distribution and operating responsibilities.

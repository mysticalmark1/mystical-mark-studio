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

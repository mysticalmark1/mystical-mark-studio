# Contributing

Contributions are accepted under AGPL-3.0-or-later. Preserve copyright and third-party notices, document meaningful changes, and do not impose extra use restrictions. Do not submit someone else's copyrighted content without appropriate rights. This project was developed with AI assistance; changes still need human review and testing.

Use synthetic transcripts, credentials, client summaries and metrics in tests. Never include real user data in issues, pull requests, screenshots or fixtures. Explain why a change is needed, its behavior and how it was verified. Keep data outside source, preserve existing records during updates and fail closed when the database version is newer than supported.

## Checks

Run `python -m unittest discover -s tests -v` with project dependencies installed and `node --check static/app.js` if Node is available. CI defines Linux, Windows and macOS jobs; a workflow file is not proof those jobs passed. Test native service/certificate steps on the relevant OS before changing their documented support status. Mock external providers in tests; never post or spend API credits as part of CI.

## Source distribution

`SOURCE_FILES.txt` explicitly lists project source, build/install scripts, documentation, tests, notices and third-party license texts. Add new source files to that list, and remove deleted paths. The `/source` endpoint regenerates an archive from those files in the running installation, rejecting symlinks and traversal. Changes to existing listed files appear immediately. Inspect the archive after changes: an allowlist does not sanitize secrets deliberately written into an allowed source file.

Retain the visible license/source links. Make the corresponding source of your modified deployment available to its network users as required by AGPL section 13. A stale upstream link alone does not provide your modifications. Include needed build/install instructions and dependency information, and meet the licensing/source requirements of bundled dependencies if you distribute a runtime or container. This release distributes project source; third-party source URLs/hashes and licenses are supplied in the notices. The Python runtime, operating-system libraries and Caddy are installed separately.

Update version.py, UI version, changelog and source manifest for each release. Publish immutable tags; do not move a public release tag to different code.

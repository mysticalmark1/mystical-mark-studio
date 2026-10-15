# Update, backup and rollback

## Existing Linux/systemd installation

1. Finish or cancel running generation tasks. Review scheduled posts; do not update while a network send is in progress. Interrupted sends are not automatically retried.
2. Download a content backup from Settings & backup and store it privately.
3. Extract the new release into a **new folder**, not over the installed `current` directory. Do not copy data into the source folder.
4. Open a terminal in the extracted `mystical-mark-studio` folder and run `bash install.sh` **without sudo**. Use the same Linux account as before.
5. Open your existing HTTPS address (or loopback HTTP if you never enabled LAN). Sign in with the same password. Inspect the planner, files, drafts, task history and private profile.

The installer prepares dependencies and tests the new code before stopping the old service. Once stopped, it copies the data directory into `backups/pre-update-TIMESTAMP-ID/`, excluding older backups and old restore rollback directories. This private snapshot includes the database/WAL, blobs, login configuration, credentials and Caddyfile. It is not a downloadable source release and must never go on GitHub. Snapshots consume disk space; remove older ones only after verifying your external backup.

It then reads the previous release's embedded description and creator instructions **without executing that source**, writes them into the private database if no profile already exists, initializes without resetting an existing account, validates the generated systemd unit, switches `current`, starts the service and checks local HTTP readiness. It preserves existing ideas and all other database records; schema remains 1. It does not reconfigure the HTTPS gateway, replace its CA, or reset your password.

The old release remains under `~/.local/lib/mystical-mark-studio/releases/`. A failed activation restores the previous link and unit and attempts to restart it. The additive profile migration may remain in the database; old code ignores this new setting. It does not automatically restore older content over your live work.

### Custom data paths

The updater reads the existing `MM_DATA_DIR` from its generated service file. If you set a conflicting `MM_DATA_DIR`, the update stops. Custom unit layouts without that setting require inspection rather than a guessed default. Do not switch data paths during the same upgrade. Services with externally customized drop-ins are not covered by the automatic recovery logic; verify their settings separately.

### Do not delete

- Your private data directory, normally `~/.local/share/mystical-mark-studio/`.
- Your existing code installation before the first public-release migration (it contains the old embedded creator instructions).
- Caddy's CA directory; deleting it would require trusting a new root on every device.

If your original planner ideas were already edited or marked used, those values stay as saved. Public new installs intentionally do not receive that personal bank.

## Manual foreground upgrade (all desktop platforms)

Stop Studio and Caddy before copying data. Make a private copy of the complete data directory outside the source checkout (and preserve Caddy's own CA storage). Extract the new code in a separate folder, create a fresh `.venv` and install `requirements.txt` following README. Keep the same `MM_DATA_DIR` for every command.

If upgrading an original private release without systemd, run the new environment's Python with:

```bash
.venv/bin/python manage.py migrate-profile /absolute/path/to/old/source
.venv/bin/python manage.py init
.venv/bin/python run.py
```

On Windows substitute `.\.venv\Scripts\python.exe` and quote Windows paths containing spaces. The migration does not overwrite an existing private profile. `init` preserves an existing account. For later public releases, profile migration is unnecessary. Restart Caddy using its existing private configuration; do not recreate its certificate authority.

Automatic activation rollback is provided only by the Linux installer. For a failed manual update, stop the new process and launch the previous source/environment against the same data (safe for this schema-1 update).

## Content ZIP backup and restore

Content backups from the UI or `manage.py backup` include the database, private profile and blobs, but **exclude login configuration, credentials and gateway config**. They are different from the full private pre-update snapshot directory. All backups may contain confidential content and are unencrypted by this app.

Installed Linux:

```bash
"$HOME/.local/lib/mystical-mark-studio/current/.venv/bin/python" "$HOME/.local/lib/mystical-mark-studio/current/manage.py" backup
"$HOME/.local/lib/mystical-mark-studio/current/.venv/bin/python" "$HOME/.local/lib/mystical-mark-studio/current/manage.py" restore /absolute/path/to/content-backup.zip
systemctl --user start mystical-mark-studio
```

Restore validates archive paths and hashes, prompts for `RESTORE`, stops the installed service and makes a safety backup. It retains the current login and credentials. Previously approved/scheduled outbound posts become drafts so an old schedule is not replayed.

For a portable install, stop **every** Studio process first, then use `manage.py restore /path/to/content-backup.zip --manual`. Confirm `STOPPED` only after doing so. Do not leave a background instance writing to the database. Restart `run.py` afterwards.

## Manual Linux code rollback

List releases and choose the exact older directory you want; do not paste an unknown path:

```bash
ls "$HOME/.local/lib/mystical-mark-studio/releases"
```

Stop the service, switch the `current` symlink to that older directory, and restart. The old 1.0 release lacks `run.py`, so its service must also use the older `app.py` entry point. The installer handles this automatically on failed activation; for a later manual rollback, restore your previous unit or update its ExecStart accordingly, run `systemctl --user daemon-reload`, and then start it. No database downgrade is required for 1.1.0 → 1.0.0.

Restore a full pre-update snapshot only with Studio stopped, after first preserving the current data separately. Copy its contents back into the same data directory with private permissions. This is a full state rollback and discards changes made after the snapshot; use it only deliberately. Caddy's CA is separate and was not changed by this update.

# Mystical Mark Studio

**A private, self-hosted creator workspace — version 1.1.1.**

Organize source files, prepare AI handoffs, review forecast claims, write scripts and keep reusable outputs in one place. This project is released for transparency, inspection, modification and sharing under **AGPL-3.0-or-later**, matching the companion astrology project's license choice. It is a separate app; it does not include Swiss Ephemeris or calculate charts.

The public release contains application source and synthetic examples. It contains no creator account, personal content bank, private description block, credentials or client files. New installs start with an empty planner. Existing installations retain their saved content and migrate their old embedded creator instructions into private database settings.

## Monthly reviews with large source sets

Version 1.1.1 removes the combined 750,000-character cap for manual Work tasks. Select all weekly registers and assessments together and prepare one monthly task. The downloaded `TASK.md` includes every selected text source in full, in selection order. Nothing is summarized, truncated or split. The existing 40-source selection limit and 25 MB per-upload limit remain. Direct API mode retains its separate safeguard and directs large reviews to Work mode. ChatGPT itself may impose file/context limits; this change removes Studio’s local cap and does not guarantee a receiving model’s capacity.

## Features

| Workspace | What it does |
|---|---|
| Create & package | Long/short-form metadata, chapters, hashtags, thumbnail tasks and optional advance registers |
| Forecast reviews | Prospective claim registers, weekly assessments, monthly reconciliation, compact monthly carry-forward tracker and yearly synthesis |
| File space | Local transcripts, reference images, PDFs and outputs with project/tag/private labels |
| Content planner | Searchable ideas, talking points, ratings and production status |
| Writing room | Scripts, saved revisions, Markdown export and conservative X/Threads splitting |
| Client summaries | Transcript-grounded summaries and local PDF export |
| Publishing desk | Draft/review/approval flow; optional credential-based text posting and local scheduling |
| Analytics | CSV imports, daily vs snapshot distinctions and exportable analysis handoffs |
| Settings | Private creator prompts, exact description insertion, timezone, model preferences and backups |

**ChatGPT Work handoff is manual.** Download a task packet, attach its files in Work, choose the model there, and import `result.json` and images back into Studio. This app cannot launch Work or control its model picker. Optional OpenAI API generation is separate, requires your own API access and may incur charges. Review generated material before publishing. Analytics are imported, not live account sync. No external account is included.

## Platform support

| Platform | Status |
|---|---|
| Linux with systemd | Primary setup; automatic install/update and user services. Existing Manjaro deployment path retained |
| Linux without systemd | Manual foreground setup below |
| Windows / macOS | Portable foreground path provided; native execution and certificate setup not verified on these operating systems |
| iPhone/iPad/Android | Browser clients of an awake host through private HTTPS; not native server installations |

Python **3.11+** is required; Python 3.12 is the tested environment for this release. A dependency wheel must be available for your Python/OS, or build tools may be needed. `tzdata` supplies timezone data where the OS does not. Windows file permissions follow account/NTFS ACLs; POSIX `chmod` alone does not provide equivalent isolation. Keep private data in your own protected user profile.

## Existing users: upgrade without resetting your account

Extract this release into a **new source folder**, then open a terminal inside `mystical-mark-studio` and run:

```bash
bash install.sh
```

Do not use sudo. Do not delete your existing installation or data. The installer stops Studio, creates a private pre-update snapshot, migrates embedded creator preferences, preserves the password and TLS settings, validates the new unit and checks startup. Code uses a new versioned directory; the old release remains available. It restores the previous code/service if activation fails. Database schema remains **1**.

Your existing HTTPS URL and trusted root certificate remain the same. Do not rerun `lan` or reset your password just to update. Read [the upgrade and rollback guide](docs/UPGRADING.md) before upgrading, especially for a custom data directory.

## New Linux/systemd install

Install Python, venv support and pip using your distribution. On Manjaro/Arch:

```bash
sudo pacman -Syu python python-pip
```

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

Download and extract a release, or clone your chosen public fork. Replace `YOUR_USERNAME` below with the repository owner:

```bash
git clone https://github.com/YOUR_USERNAME/mystical-mark-studio.git
cd mystical-mark-studio
bash install.sh
```

Run the installer as your normal user. Choose a password of at least 14 characters on first installation. Open **http://127.0.0.1:8765**. In **Settings & backup**, fill in your private creator profile before preparing tasks.

For service startup before login (optional):

```bash
sudo loginctl enable-linger "$USER"
```

## Portable setup: macOS or Linux

Install Python 3.11+ and extract the source to a folder you own. From that folder:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py init
.venv/bin/python run.py
```

Keep the terminal open. Ctrl+C stops the app, including scheduling. Do not run the portable server alongside an installed instance pointing to the same database.

## Portable setup: Windows PowerShell

Install Python 3.11+ from [python.org](https://www.python.org/downloads/), including the Python launcher. Extract the source, open PowerShell in that folder, then:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py init
.\.venv\Scripts\python.exe run.py
```

No activation script or execution-policy change is necessary. Open **http://127.0.0.1:8765**. Keep PowerShell open; Ctrl+C stops the app. Use the same account and data directory for each run.

## Private data and credentials

On every platform, the default is `<your home>/.local/share/mystical-mark-studio/`. This intentionally preserves the original Linux location; on Windows it is normally under `%USERPROFILE%`. Set `MM_DATA_DIR` to an absolute private location **outside the source tree** if needed, consistently for all commands. An existing systemd installation's configured path is recovered on update; conflicting overrides are rejected.

The directory contains `studio.sqlite3`, `blobs/`, `backups/`, private `config.json`, optional `secrets.env`, and optional `Caddyfile`. Never upload it to GitHub. Creator profiles are database settings and are included in content backups. Caddy's certificate authority is kept separately in Caddy's own storage.

For optional credentials on an installed Linux instance:

```bash
"$HOME/.local/lib/mystical-mark-studio/current/.venv/bin/python" "$HOME/.local/lib/mystical-mark-studio/current/manage.py" credentials
systemctl --user restart mystical-mark-studio
```

For portable installs use your `.venv` Python with `manage.py credentials`, then restart `run.py`. Inputs are hidden. Keys are saved locally, not in source. `run.py` reads only the supported credential names; explicit environment values take precedence. Keep API mode disabled unless you intend to send selected content.

## Phones, HTTPS and VPN

Install Caddy and follow [HTTPS and certificate trust](docs/HTTPS.md), covering Linux/Zen/Firefox, Windows, macOS, iPhone/iPad, Android and ChromeOS. The app binds **127.0.0.1:8765**; Caddy listens on the chosen private IP at **9443** and permits only configured client subnets. Use the printed HTTPS URL on desktop as well once LAN mode is enabled.

This is a single-user private application, not a hardened public multi-tenant service. Do not expose it using router forwarding or public tunnels. VPN routing/firewall settings are managed separately. The app and gateway must both be running and the host awake.

## Backups and daily use

Use **Settings & backup → Download full backup** for database and blobs. These content ZIPs exclude login/credentials/gateway config; preserve those separately or use the installer's private pre-update snapshot. Backups are not encrypted. See [UPGRADING.md](docs/UPGRADING.md) for restore and rollback.

Read [WORKFLOWS.md](docs/WORKFLOWS.md) for task handoffs, forecasting, posting and analytics. `examples/` contains synthetic input formats. Creator context is editable privately; the public prompt templates contain no personal creator information. Saved tasks retain their original prompts; changing your profile applies to newly prepared tasks.

## Development and source transparency

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

Use the Windows Python path shown above on Windows. The UI is plain HTML/CSS/JavaScript, without a build system. Python handles HTTP, SQLite storage, task construction, API transport, exports and scheduling. See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [verification notes](VALIDATION.md).

The login page and app footer offer **License** and **Download source** links. `/source` generates an archive from the running source files listed in `SOURCE_FILES.txt`, excluding private data, virtual environments and unknown files. If you add source/build files, update that manifest and inspect the generated archive. Never add runtime data or secrets to it. Dependency versions and upstream source locations are recorded separately.

## License and publishing

This project's original code, documentation and bundled prompt templates are **GNU AGPL version 3 or later**, without warranty; see [LICENSE](LICENSE) and [NOTICE](NOTICE). Third-party packages retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The license does not transfer ownership of uploaded/generated content or require publishing private user data. No additional restriction on commercial use or field of use is imposed.

Preserve notices and provide the corresponding source when the license requires it, including for modified versions used over a network. Keep the source offer aligned with the version actually served. [GNU's AGPL text](https://www.gnu.org/licenses/agpl-3.0.html) is authoritative. An AGPL license promotes access to source; it does not guarantee ethical use or prevent every misuse.

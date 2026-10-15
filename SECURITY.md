# Security and privacy

Studio is a private single-user tool. Keep the backend on loopback and use the provided Caddy TLS gateway with private subnet filtering for LAN/VPN access. Do not expose it publicly. Login, host/origin checks and CSRF protection are not substitutes for network access control.

Credentials are stored in the private data directory, never the browser's settings payload. Provider/API mode and publishing send selected material to external services only through those workflows. Work packets are downloaded locally, then sent manually by the operator. Private flags require confirmation before generation, but backups, saved task prompts and exported packets can still contain that material. Deleting one source blob does not erase copies in task history or backups.

The source endpoint is available without login so network users can inspect the program. It exposes only manifest-listed project files, not arbitrary paths or data. Do not put private material in project code, prompt templates or the manifest. Use the database's private creator profile.

If the project repository enables GitHub private vulnerability reporting, use its **Security → Report a vulnerability** flow. Otherwise ask the maintainer for a private reporting channel without posting credentials, real client data or exploit details in a public issue. Rotate exposed tokens and passwords; removing a file from a later commit does not erase it from Git history.

No public security audit is claimed. OS/browser certificate installation and live third-party integrations require validation in the deployment environment. Optional provider endpoints and permissions may change independently of this app.

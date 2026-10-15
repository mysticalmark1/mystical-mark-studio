# Third-party notices

Studio original source is AGPL-3.0-or-later. Dependencies are separately installed by pip under their own licenses; they are not relicensed by this project. Full copyright/license texts recovered from the pinned package metadata are retained in `third_party/`.

| Package | Pinned version | License | Source/project |
|---|---|---|---|
| blinker | 1.9.0 | MIT | [Upstream](https://pypi.org/project/blinker/1.9.0/) |
| charset-normalizer | 3.5.2 | MIT | [Upstream](https://pypi.org/project/charset-normalizer/3.5.2/) |
| click | 8.5.0 | BSD-3-Clause | [Upstream](https://pypi.org/project/click/8.5.0/) |
| Flask | 3.1.2 | BSD-3-Clause | [Upstream](https://pypi.org/project/Flask/3.1.2/) |
| itsdangerous | 2.2.0 | BSD-3-Clause | [Upstream](https://pypi.org/project/itsdangerous/2.2.0/) |
| Jinja2 | 3.1.6 | BSD-3-Clause | [Upstream](https://pypi.org/project/Jinja2/3.1.6/) |
| MarkupSafe | 3.0.4 | BSD-3-Clause | [Upstream](https://pypi.org/project/MarkupSafe/3.0.4/) |
| pillow | 11.3.0 | MIT-CMU | [Upstream](https://pypi.org/project/pillow/11.3.0/) |
| reportlab | 4.4.4 | BSD license (see license.txt for details), Copyright (c) 2000-2025, ReportLab Inc. | [Upstream](https://pypi.org/project/reportlab/4.4.4/) |
| waitress | 3.0.2 | ZPL 2.1 | [Upstream](https://pypi.org/project/waitress/3.0.2/) |
| Werkzeug | 3.1.9 | BSD-3-Clause | [Upstream](https://pypi.org/project/Werkzeug/3.1.9/) |
| tzdata | 2026.1 | Apache-2.0 | [Upstream](https://pypi.org/project/tzdata/2026.1/) |
| colorama | 0.4.6 | BSD-3-Clause | [Upstream](https://pypi.org/project/colorama/0.4.6/) |

`third_party/dependencies.json` records exact upstream source archive URLs and SHA-256 digests for these pinned versions. These references are available in the in-app source archive. Download and retain matching dependency sources/notices when packaging a complete runtime, container or modified combined distribution; do not assume a project-only archive covers added dependencies.

Pillow distributions may contain additional native-library notices in their full LICENSE; these are preserved. ReportLab distributions may bundle fonts with separate terms in their LICENSE. tzdata includes IANA data with public-domain portions; the package license texts are preserved. Colorama is a Windows-only dependency of Click. Python/SQLite and optional Caddy are separate system/runtime components, not bundled here. Caddy is Apache-2.0: https://github.com/caddyserver/caddy/blob/master/LICENSE.

No third-party JavaScript framework, remote font, icon package or image-generation asset is bundled. The SVG icon and UI styles are project source. Private user uploads and generated outputs are not part of this source release; their rights depend on their own provenance.

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Mystical Mark Studio contributors
# Distributed WITHOUT ANY WARRANTY. See LICENSE and NOTICE.
"""Wait briefly for the local server to answer; no credentials or private data sent."""
import time, urllib.request, urllib.error

def main():
    for attempt in range(30):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8765/api/session',timeout=1) as response:
                if response.status==200: return
        except (OSError,urllib.error.URLError): pass
        time.sleep(0.5)
    raise SystemExit('Studio did not become ready; check the user service journal.')
if __name__=='__main__': main()

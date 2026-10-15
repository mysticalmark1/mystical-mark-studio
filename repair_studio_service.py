#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Mystical Mark Studio contributors
# Distributed WITHOUT ANY WARRANTY. See LICENSE and NOTICE.
"""Repair the v1 WorkingDirectory quoting error without changing app data."""
from pathlib import Path
from datetime import datetime
import os
import shutil
import subprocess
import sys


def repair_text(text):
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        for key in ('WorkingDirectory', 'EnvironmentFile'):
            prefix = key + '='
            if line.startswith(prefix + '"'):
                value = line[len(prefix):].rstrip('\r\n')
                if value.endswith('"'):
                    lines[index] = prefix + value[1:-1] + '\n'
            elif line.startswith(prefix + '-"'):
                value = line[len(prefix) + 1:].rstrip('\r\n')
                if value.endswith('"'):
                    lines[index] = prefix + '-' + value[1:-1] + '\n'
    return ''.join(lines)


def main():
    if os.geteuid() == 0:
        raise SystemExit('Run this as your normal user, without sudo.')
    unit = Path.home() / '.config/systemd/user/mystical-mark-studio.service'
    if not unit.is_file():
        raise SystemExit('Studio service not found: ' + str(unit))
    original = unit.read_text(encoding='utf-8')
    fixed = repair_text(original)
    if fixed != original:
        backup = unit.with_name(unit.name + '.before-fix-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        shutil.copy2(unit, backup)
        candidate = unit.with_name('mystical-mark-studio-repair.service')
        try:
            candidate.write_text(fixed)
            os.chmod(candidate, 0o600)
            check = subprocess.run(['systemd-analyze', '--user', 'verify', str(candidate)], capture_output=True, text=True)
            if check.returncode:
                print(check.stdout + check.stderr, file=sys.stderr)
                raise SystemExit('Validation failed. Your original service was left unchanged. Please share the output above.')
            candidate.replace(unit)
        finally:
            candidate.unlink(missing_ok=True)
        print('Service path repaired. Original service backed up to:', backup)
    else:
        print('Service path settings are already unquoted; checking service startup.')
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'reset-failed', 'mystical-mark-studio'], check=False)
    subprocess.run(['systemctl', '--user', 'restart', 'mystical-mark-studio'], check=True)
    result = subprocess.run(['systemctl', '--user', 'status', 'mystical-mark-studio', '--no-pager', '--full'])
    if result.returncode:
        raise SystemExit('The unit repair is complete, but startup needs another check. Please share the status output above.')
    print('\nOpen http://127.0.0.1:8765 (or your configured private HTTPS address).')
    print('Your password, database, saved files and credentials were not changed.')


if __name__ == '__main__':
    main()

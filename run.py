#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Mystical Mark Studio contributors
# Distributed WITHOUT ANY WARRANTY. See LICENSE and NOTICE.
"""Portable foreground launcher. Keep this terminal open; Ctrl+C stops Studio."""
import os
from storage import data_path


def load_credentials():
    path=data_path()/'secrets.env'
    allowed={'OPENAI_API_KEY','X_USER_ACCESS_TOKEN','THREADS_ACCESS_TOKEN','THREADS_USER_ID'}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            key,sep,value=line.partition('=')
            if sep and key in allowed: os.environ.setdefault(key,value)

if __name__=='__main__':
    load_credentials()
    from app import main
    main()

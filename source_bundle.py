# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Mystical Mark Studio contributors
# Distributed WITHOUT ANY WARRANTY. See LICENSE and NOTICE.
"""Offer running source from an explicit manifest, never the private data directory."""
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED


def source_files(root):
    root=Path(root).resolve()
    for entry in (root/'SOURCE_FILES.txt').read_text(encoding='utf-8').splitlines():
        if not entry or entry.startswith('#'): continue
        rel=Path(entry)
        if rel.is_absolute() or '..' in rel.parts: raise ValueError('Invalid source manifest path')
        path=root/rel
        if any((root/Path(*rel.parts[:i])).is_symlink() for i in range(1,len(rel.parts)+1)):
            raise ValueError('Source manifest cannot contain symlinks')
        if not path.is_file(): raise ValueError('Missing source file: '+entry)
        yield path


def build_source_archive(root):
    root=Path(root).resolve(); stream=BytesIO()
    with ZipFile(stream,'w',ZIP_DEFLATED) as z:
        for path in source_files(root): z.write(path,Path('mystical-mark-studio')/path.relative_to(root))
    return stream.getvalue()

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
    a.output.write_bytes(build_source_archive(Path(__file__).resolve().parent))
    print('Source archive created:',a.output)

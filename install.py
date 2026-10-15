#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Mystical Mark Studio contributors
# Distributed WITHOUT ANY WARRANTY. See LICENSE and NOTICE.
"""Linux/systemd installer with pre-update snapshot, profile migration and rollback."""
import getpass, json, os, pathlib, shutil, subprocess, sys, time, uuid
from source_bundle import source_files
from version import VERSION


def run(args,**kw): return subprocess.run(args,check=True,**kw)


def unit_text(current,data):
    def q(value):
        value=str(value)
        if any(c in value for c in '\n\r\x00'): raise ValueError('Unsupported control character in install path')
        return value.replace('\\','\\\\').replace('%','%%').replace('"','\\"')
    return ('[Unit]\nDescription=Mystical Mark Studio\nAfter=network-online.target\n\n[Service]\nType=simple\n'
        'WorkingDirectory='+q(current)+'\nEnvironment="MM_DATA_DIR='+q(data)+'"\n'
        'EnvironmentFile=-'+q(data/'secrets.env')+'\n'
        'ExecStart="'+q(current/'.venv/bin/python')+'" "'+q(current/'run.py')+'"\n'
        'Restart=on-failure\nRestartSec=5\nUMask=0077\nNoNewPrivileges=true\nPrivateTmp=true\n'
        'ProtectSystem=strict\nReadWritePaths="'+q(data)+'"\n\n[Install]\nWantedBy=default.target\n')


def installed_data_path(unit):
    """Recover the app's existing custom data path; fail closed for unrecognized units."""
    if not unit.exists(): return None
    import shlex
    for line in unit.read_text(encoding='utf-8').splitlines():
        if line.startswith('Environment='):
            for value in shlex.split(line.split('=',1)[1]):
                if value.startswith('MM_DATA_DIR='):
                    return pathlib.Path(value.split('=',1)[1].replace('%%','%')).expanduser().resolve()
    raise ValueError('Cannot identify existing MM_DATA_DIR. Inspect your service before upgrading.')


def snapshot_data(data, destination):
    # Called only after stopping the application, so WAL/database/blobs are consistent.
    # Includes private account, credentials and gateway configuration; excludes older backups.
    shutil.copytree(data,destination,ignore=shutil.ignore_patterns('backups','pre-update-*','restore-rollback-*'))
    os.chmod(destination,0o700)
    return destination


def switch_link(current,target):
    link=current.with_name('current.next')
    link.unlink(missing_ok=True);link.symlink_to(target);link.replace(current)


def main():
    if not sys.platform.startswith('linux') or not shutil.which('systemctl'):
        raise SystemExit('This installer requires Linux/systemd. See README for portable Windows/macOS/Linux setup.')
    if os.geteuid()==0: raise SystemExit('Run as your normal user, without sudo.')
    if sys.version_info<(3,11): raise SystemExit('Python 3.11 or later is required.')
    source=pathlib.Path(__file__).resolve().parent
    base=pathlib.Path.home()/'.local/lib/mystical-mark-studio'
    units=pathlib.Path.home()/'.config/systemd/user';units.mkdir(parents=True,exist_ok=True)
    unit=units/'mystical-mark-studio.service'
    known=installed_data_path(unit)
    explicit=os.environ.get('MM_DATA_DIR')
    data=pathlib.Path(explicit).expanduser().resolve() if explicit else (known or pathlib.Path.home()/'.local/share/mystical-mark-studio')
    if known and data!=known: raise SystemExit('MM_DATA_DIR differs from the installed service. Refusing an unintended data-directory change.')
    if data==source or data.is_relative_to(source): raise SystemExit('Keep MM_DATA_DIR outside the source folder.')
    base.mkdir(parents=True,exist_ok=True);data.mkdir(parents=True,exist_ok=True,mode=0o700)
    current=base/'current'; previous=current.resolve() if current.exists() else None
    if current.exists() and not current.is_symlink(): raise SystemExit('Expected current to be a symlink; no files changed.')
    release=base/'releases'/(VERSION+'-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])
    release.mkdir(parents=True)
    for path in source_files(source):
        target=release/path.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    run([sys.executable,'-m','venv',str(release/'.venv')])
    py=release/'.venv/bin/python'
    run([str(py),'-m','pip','install','--requirement',str(release/'requirements.txt')])
    run([str(py),'-m','unittest','discover','-s','tests','-q'],cwd=release)
    env={**os.environ,'MM_DATA_DIR':str(data)}
    old_unit=unit.read_bytes() if unit.exists() else None
    stopped=False; switched=False
    try:
        if previous:
            run(['systemctl','--user','stop','mystical-mark-studio']);stopped=True
            backup=snapshot_data(data,data/'backups'/('pre-update-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]))
            print('Private pre-update snapshot:',backup)
            run([str(py),str(release/'manage.py'),'migrate-profile',str(previous)],env=env)
        run([str(py),str(release/'manage.py'),'init'],env=env)
        # Validate the new service against the real release before changing the current link.
        candidate=units/'mystical-mark-studio-verify.service'
        try:
            candidate.write_text(unit_text(release,data))
            run(['systemd-analyze','--user','verify',str(candidate)])
            switch_link(current,release);switched=True
            candidate.write_text(unit_text(current,data));candidate.replace(unit)
        finally: candidate.unlink(missing_ok=True)
        run(['systemctl','--user','daemon-reload'])
        run(['systemctl','--user','enable','--now','mystical-mark-studio'])
        # Startup may return before Python imports/configuration finish. Verify local HTTP readiness.
        run([str(py),str(release/'healthcheck.py')],env=env)
        config=json.loads((data/'config.json').read_text(encoding='utf-8'))
        print('\nInstalled Studio '+VERSION+'. Open '+config.get('origin','http://127.0.0.1:8765'))
        print('Existing HTTPS gateway/certificates, login and content are preserved.')
        print('For startup before login, run once: sudo loginctl enable-linger '+getpass.getuser())
    except Exception:
        if previous and stopped:
            if switched: switch_link(current,previous)
            if old_unit is not None: unit.write_bytes(old_unit)
            subprocess.run(['systemctl','--user','daemon-reload'])
            subprocess.run(['systemctl','--user','restart','mystical-mark-studio'])
            print('Previous release restored. Private pre-update snapshot retained.',file=sys.stderr)
        raise

if __name__=='__main__': main()

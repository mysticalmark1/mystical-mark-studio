#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Mystical Mark Studio contributors
# Distributed WITHOUT ANY WARRANTY. See LICENSE and NOTICE.
"""Local account, private network setup, backup and guarded restore."""
import argparse, getpass, ipaddress, json, os, re, secrets, shutil, sqlite3, subprocess, sys, tempfile, zipfile
from pathlib import Path
from storage import Store, data_path, SCHEMA
from werkzeug.security import generate_password_hash

def write_private(path,text):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    tmp=path.with_suffix(path.suffix+'.new'); tmp.write_text(text,encoding='utf-8'); os.chmod(tmp,0o600); tmp.replace(path)

def password():
    p=getpass.getpass('Choose a studio password (at least 14 characters): ')
    if len(p)<14: raise ValueError('Use at least 14 characters, ideally a long passphrase.')
    if p!=getpass.getpass('Repeat the password: '): raise ValueError('Passwords differ')
    return generate_password_hash(p,method='scrypt')

def init(reset=False):
    store=Store(); path=store.path/'config.json'
    if path.exists() and not reset:
        print('Existing account preserved. Use reset-password to change it.'); return
    config=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'hosts':['localhost','127.0.0.1'],'origin':'http://127.0.0.1:8765','secure_cookie':False}
    config.update(secret=secrets.token_hex(32),password_hash=password())
    write_private(path,json.dumps(config,indent=2)); print('Local account saved. Existing content was preserved.')

def credentials():
    store=Store(); path=store.path/'secrets.env'
    current={}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if '=' in line: k,v=line.split('=',1); current[k]=v
    print('Optional credentials. Enter keeps the current value; a single - removes it. No credential is sent now.')
    for key in ['OPENAI_API_KEY','X_USER_ACCESS_TOKEN','THREADS_ACCESS_TOKEN','THREADS_USER_ID']:
        value=getpass.getpass(key+': ').strip()
        if value=='-': current.pop(key,None)
        elif value:
            if not re.fullmatch(r'[A-Za-z0-9_.~+/=:%-]+',value): raise ValueError('Unexpected token characters; no changes saved.')
            current[key]=value
    write_private(path,'\n'.join(k+'='+v for k,v in current.items())+'\n')
    print('Credentials saved privately. Restart Studio (systemctl --user restart mystical-mark-studio, or restart python run.py for manual installs).')

def restore(archive, manual=False):
    archive=Path(archive).expanduser().resolve()
    root=data_path()
    if not archive.is_file(): raise ValueError('Backup does not exist')
    stage=Path(tempfile.mkdtemp(prefix='mm-restore-',dir=root.parent)); os.chmod(stage,0o700)
    try:
        with zipfile.ZipFile(archive) as z:
            infos=z.infolist()
            if sum(x.file_size for x in infos)>10*1024**3 or len(infos)>100000: raise ValueError('Backup exceeds restore limits')
            names=[x.filename for x in infos]
            if len(set(names))!=len(names): raise ValueError('Duplicate archive paths rejected')
            for info in infos:
                if info.filename not in ('manifest.json','studio.sqlite3') and not re.fullmatch(r'blobs/[a-f0-9]{32}',info.filename): raise ValueError('Unexpected archive path')
                if (info.external_attr>>16)&0o170000==0o120000: raise ValueError('Archive symlinks are not allowed')
            manifest=json.loads(z.read('manifest.json'))
            if manifest.get('format')!='mystical-mark-studio' or manifest.get('schema')!=SCHEMA: raise ValueError('Unsupported backup version')
            z.extractall(stage)
        test=sqlite3.connect(stage/'studio.sqlite3')
        if test.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Database integrity check failed')
        if test.execute('PRAGMA user_version').fetchone()[0]!=SCHEMA: raise ValueError('Database version mismatch')
        import hashlib
        for id_,sha in test.execute('SELECT id,sha256 FROM files'):
            if not re.fullmatch(r'[a-f0-9]{32}',id_): raise ValueError('Invalid blob ID')
            p=stage/'blobs'/id_
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha: raise ValueError('A backup file is missing or damaged')
        # Never replay scheduled outbound operations restored from an old backup.
        for id_,body in test.execute("SELECT id,body FROM entities WHERE type='post'").fetchall():
            b=json.loads(body)
            if b.get('state') in ('approved','scheduled','publishing'):
                b['state']='draft'; b['approved_at']=''; b['error']='Restored backup: review the platform before approving again.'
                test.execute('UPDATE entities SET body=? WHERE id=?',(json.dumps(b),id_))
        test.commit(); test.close()
        print('Validated backup:',archive.name)
        if input('Restore replaces current content. Type RESTORE to proceed: ')!='RESTORE': print('Cancelled.'); return
        if manual:
            if input('Stop every Studio process first. Type STOPPED to confirm: ')!='STOPPED': raise ValueError('Restore cancelled')
            stopped=None
        else: stopped=subprocess.run(['systemctl','--user','stop','mystical-mark-studio'],capture_output=True)
        if stopped is not None and stopped.returncode: raise ValueError('Could not stop the user service. Stop any running app, then restore from an installed session.')
        store=Store(root); safety=store.backup()
        # Staged rollback directory protects against an interrupted restore.
        rollback=root/('restore-rollback-'+secrets.token_hex(4)); rollback.mkdir(mode=0o700)
        for name in ('studio.sqlite3','studio.sqlite3-wal','studio.sqlite3-shm','blobs'):
            p=root/name
            if p.exists(): p.rename(rollback/name)
        try:
            (stage/'studio.sqlite3').rename(root/'studio.sqlite3')
            (stage/'blobs').mkdir(exist_ok=True)
            (stage/'blobs').rename(root/'blobs')
            os.chmod(root/'studio.sqlite3',0o600); os.chmod(root/'blobs',0o700)
            for p in (root/'blobs').iterdir(): os.chmod(p,0o600)
        except Exception:
            for name in ('studio.sqlite3','blobs'):
                p=root/name
                if p.is_dir(): shutil.rmtree(p)
                elif p.exists(): p.unlink()
            for p in rollback.iterdir(): p.rename(root/p.name)
            raise
        print('Restored. Credentials and login preserved. Safety backup:',safety.name)
        print('Start the app: python run.py' if manual else 'Start the app: systemctl --user start mystical-mark-studio')
    finally: shutil.rmtree(stage,ignore_errors=True)

def lan(manual=False):
    if not shutil.which('caddy'): raise ValueError('Install Caddy first: sudo pacman -S caddy')
    store=Store(); path=store.path/'config.json'
    config=json.loads(path.read_text(encoding='utf-8'))
    addr=input('This computer’s fixed private IPv4 address (LAN or WireGuard): ').strip()
    ip=ipaddress.ip_address(addr)
    allowed=[ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')]
    if ip.version!=4 or not any(ip in n for n in allowed): raise ValueError('Use an RFC1918 private IPv4 address, not a public or wildcard address.')
    cidrs=input('Allowed client LAN/VPN CIDRs, separated by spaces (for example 192.168.1.0/24): ').split()
    if not cidrs: raise ValueError('At least one client subnet is required')
    for value in cidrs:
        net=ipaddress.ip_network(value,strict=True)
        if net.version!=4 or not any(net.subnet_of(n) for n in allowed): raise ValueError('Client CIDRs must be contained in private IPv4 ranges')
    conf=store.path/'Caddyfile'
    write_private(conf,'{\n admin off\n auto_https disable_redirects\n}\nhttps://'+addr+':9443 {\n bind '+addr+'\n tls internal\n @private remote_ip '+ ' '.join(cidrs)+'\n handle @private {\n  reverse_proxy 127.0.0.1:8765\n }\n handle {\n  respond "Private network only" 403\n }\n}\n')
    config.update(hosts=['localhost','127.0.0.1',addr],origin='https://'+addr+':9443',secure_cookie=True)
    write_private(path,json.dumps(config,indent=2))
    if manual:
        print('Gateway config written:',conf)
        print('Restart Studio, then run: caddy run --config PATH_TO_CADDYFILE --adapter caddyfile')
        print('Private HTTPS address: https://'+addr+':9443')
        return
    units=Path.home()/'.config/systemd/user'; units.mkdir(parents=True,exist_ok=True)
    caddy=shutil.which('caddy')
    unit='[Unit]\nDescription=Mystical Mark private HTTPS gateway\nAfter=network-online.target mystical-mark-studio.service\nWants=network-online.target\n\n[Service]\nExecStart="'+caddy+'" run --config "'+str(conf)+'" --adapter caddyfile\nRestart=on-failure\nRestartSec=5\nUMask=0077\nNoNewPrivileges=true\nPrivateTmp=true\n\n[Install]\nWantedBy=default.target\n'
    write_private(units/'mystical-mark-https.service',unit)
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    subprocess.run(['systemctl','--user','restart','mystical-mark-studio'],check=True)
    subprocess.run(['systemctl','--user','enable','--now','mystical-mark-https'],check=True)
    print('Private HTTPS address: https://'+addr+':9443')
    print('Trust ONLY the generated Caddy root certificate on your own computer and phone. See README for paths and iOS instructions.')
    print('Keep router port forwarding off. Allow TCP 9443 only from the configured LAN/VPN subnets in your firewall.')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('command',choices=['init','reset-password','credentials','backup','restore','lan','local-only','migrate-profile']);p.add_argument('file',nargs='?');p.add_argument('--manual',action='store_true',help='Foreground installation: manage app/gateway processes yourself');a=p.parse_args()
    try:
        if a.command=='init': init()
        elif a.command=='reset-password': init(True)
        elif a.command=='credentials': credentials()
        elif a.command=='backup': print(Store().backup())
        elif a.command=='restore': restore(a.file or '',a.manual)
        elif a.command=='lan': lan(a.manual)
        elif a.command=='migrate-profile':
            from studio_profile import migrate_legacy_profile
            print('Private profile migrated.' if migrate_legacy_profile(Store(),a.file or '') else 'Profile already present or no legacy profile found.')
        elif a.command=='local-only':
            if not a.manual: subprocess.run(['systemctl','--user','disable','--now','mystical-mark-https'],check=True)
            path=data_path()/'config.json'; config=json.loads(path.read_text(encoding='utf-8')); config.update(hosts=['localhost','127.0.0.1'],origin='http://127.0.0.1:8765',secure_cookie=False)
            write_private(path,json.dumps(config,indent=2))
            if not a.manual: subprocess.run(['systemctl','--user','restart','mystical-mark-studio'],check=True)
            print('Local-only access restored: http://127.0.0.1:8765')
    except (ValueError,RuntimeError,FileNotFoundError,subprocess.CalledProcessError) as e:
        print('Setup stopped:',e,file=sys.stderr);sys.exit(1)

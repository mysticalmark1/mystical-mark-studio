# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Mystical Mark Studio contributors
# Distributed WITHOUT ANY WARRANTY. See LICENSE and NOTICE.
"""Local persistence. Code and user data never share an update directory."""
import contextlib, hashlib, io, json, os, re, sqlite3, threading, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCK = threading.RLock()
SCHEMA = 1

def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return uuid.uuid4().hex

def data_path():
    return Path(os.environ.get('MM_DATA_DIR', str(Path.home()/'.local/share/mystical-mark-studio'))).expanduser().resolve()

class Store:
    def __init__(self, path=None):
        self.path = Path(path or data_path())
        self.path.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path, 0o700)
        (self.path/'blobs').mkdir(exist_ok=True, mode=0o700)
        (self.path/'backups').mkdir(exist_ok=True, mode=0o700)
        self.database = self.path/'studio.sqlite3'
        with self.connect() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version > SCHEMA: raise RuntimeError('Database is newer than this app; refusing to downgrade.')
            if version and version < SCHEMA: self.backup()
            db.executescript('''
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS files (id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
                    project TEXT NOT NULL DEFAULT '', tags TEXT NOT NULL DEFAULT '', private INTEGER NOT NULL DEFAULT 0,
                    sha256 TEXT NOT NULL, size INTEGER NOT NULL, created TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS entities (id TEXT PRIMARY KEY, type TEXT NOT NULL, body TEXT NOT NULL,
                    created TEXT NOT NULL, updated TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS entity_type ON entities(type);
                CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
                    state TEXT NOT NULL, body TEXT NOT NULL, result TEXT NOT NULL DEFAULT '{}', error TEXT NOT NULL DEFAULT '',
                    created TEXT NOT NULL, updated TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS metrics (id TEXT PRIMARY KEY, platform TEXT NOT NULL, account TEXT NOT NULL,
                    content_id TEXT NOT NULL, date TEXT NOT NULL, metric TEXT NOT NULL, value REAL NOT NULL,
                    basis TEXT NOT NULL, UNIQUE(platform,account,content_id,date,metric,basis));
                PRAGMA user_version=1;
            ''')
        os.chmod(self.database,0o600)
        if not self.get('seeded'):
            self.seed()
    def recover_interrupted(self):
        with self.connect() as db:
            db.execute("UPDATE jobs SET state='interrupted', error='The app stopped during generation. Review saved outputs before running a new job.' WHERE state IN ('queued','running')")
            rows=db.execute("SELECT * FROM entities WHERE type='post'").fetchall()
            for row in rows:
                body=json.loads(row['body'])
                if body.get('state')=='publishing':
                    body['state']='uncertain'; body['error']='Interrupted during publishing. Check the platform before retrying.'
                    db.execute('UPDATE entities SET body=? WHERE id=?',(json.dumps(body),row['id']))

    @contextlib.contextmanager
    def connect(self):
        with LOCK:
            db=sqlite3.connect(self.database, timeout=30)
            db.row_factory=sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('PRAGMA journal_mode=WAL')
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback(); raise
            finally: db.close()

    def get(self,key,default=None):
        with self.connect() as db:
            r=db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
            return json.loads(r[0]) if r else default
    def set(self,key,value):
        with self.connect() as db: db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,json.dumps(value)))
    def seed(self):
        self.set('seeded',True)
        self.set('preferences',{'mode':'work','model':'gpt-6-astra','effort':'medium','image_model':'gpt-image-2.5-sunburst'})

    def entity_save(self,type_,body,id_=None):
        id_=id_ or uid()
        with self.connect() as db:
            old=db.execute('SELECT * FROM entities WHERE id=?',(id_,)).fetchone()
            if old and old['type']!=type_: raise ValueError('Record type cannot change')
            if old and type_=='draft':
                db.execute('INSERT INTO entities VALUES (?,?,?,?,?)',(uid(),'revision',json.dumps({'draft_id':id_,'body':json.loads(old['body'])}),now(),now()))
            db.execute('INSERT INTO entities VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body,updated=excluded.updated',
                (id_,type_,json.dumps(body,ensure_ascii=False),now(),now()))
        return id_
    def entities(self,type_):
        with self.connect() as db:
            return [dict(id=r['id'],created=r['created'],updated=r['updated'],**json.loads(r['body'])) for r in db.execute('SELECT * FROM entities WHERE type=? ORDER BY updated DESC',(type_,))]
    def entity(self,id_):
        with self.connect() as db:
            r=db.execute('SELECT * FROM entities WHERE id=?',(id_,)).fetchone()
            if not r: raise ValueError('Record not found')
            return {'id':r['id'],'type':r['type'],**json.loads(r['body'])}
    def add_file(self,name,content,kind='document',project='',tags='',private=False):
        name=re.sub(r'[\x00-\x1f/\\]','_',str(name)).strip()[:180] or 'document.txt'
        if isinstance(content,str): content=content.encode('utf-8')
        id_=uid()
        with LOCK:
            p=self.path/'blobs'/id_
            p.write_bytes(content); os.chmod(p,0o600)
            try:
                with self.connect() as db:
                    db.execute('INSERT INTO files VALUES (?,?,?,?,?,?,?,?,?,?)',
                      (id_,name,kind,project,tags,int(private),hashlib.sha256(content).hexdigest(),len(content),now(),0))
            except Exception:
                p.unlink(missing_ok=True); raise
        return id_
    def file(self,id_):
        with self.connect() as db:
            r=db.execute('SELECT * FROM files WHERE id=?',(id_,)).fetchone()
            if not r: raise ValueError('File not found')
            return dict(r)
    def bytes(self,id_):
        self.file(id_)
        if not re.fullmatch(r'[a-f0-9]{32}',id_): raise ValueError('Invalid file ID')
        return (self.path/'blobs'/id_).read_bytes()
    def files(self):
        with self.connect() as db: return [dict(r) for r in db.execute('SELECT * FROM files ORDER BY created DESC')]
    def backup(self):
        with LOCK:
            target=self.path/'backups'/f'studio-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")}-{uid()[:6]}.zip'
            snapshot=self.path/f'.snapshot-{uid()}.db'
            with self.connect() as source:
                dest=sqlite3.connect(snapshot)
                source.backup(dest); dest.close()
            try:
                with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
                    z.write(snapshot,'studio.sqlite3')
                    for p in sorted((self.path/'blobs').iterdir()):
                        if p.is_file() and not p.is_symlink(): z.write(p,'blobs/'+p.name)
                    z.writestr('manifest.json',json.dumps({'format':'mystical-mark-studio','schema':SCHEMA,'created':now(),'credentials_included':False}))
            finally: snapshot.unlink(missing_ok=True)
            os.chmod(target,0o600)
            return target
    def new_job(self,kind,title,body,state):
        id_=uid()
        with self.connect() as db: db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)',(id_,kind,title,state,json.dumps(body), '{}','',now(),now()))
        return id_
    def update_job(self,id_,state,result=None,error=''):
        with self.connect() as db:
            if result is None: result=json.loads(db.execute('SELECT result FROM jobs WHERE id=?',(id_,)).fetchone()[0])
            db.execute('UPDATE jobs SET state=?,result=?,error=?,updated=? WHERE id=?',(state,json.dumps(result),error,now(),id_))
    def jobs(self):
        with self.connect() as db:
            return [dict(r,body=json.loads(r['body']),result=json.loads(r['result'])) for r in db.execute('SELECT * FROM jobs ORDER BY created DESC')]

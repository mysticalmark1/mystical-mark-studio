# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Mystical Mark Studio contributors
# Distributed WITHOUT ANY WARRANTY. See LICENSE and NOTICE.
import base64, csv, io, ipaddress, json, mimetypes, os, re, secrets, threading, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from flask import Flask, request, session, jsonify, send_file, abort
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import HTTPException
from storage import Store, ROOT, LOCK, now
from workflows import KINDS, build_prompt, packet, split_posts, expected
from ai import run_api, import_result, ProviderError, request_json
from pdf_export import make_pdf
from publishing import connections, publish, tick

from studio_profile import get_profile, validate_profile
from version import VERSION
from source_bundle import build_source_archive

ALLOWED_KINDS={'transcript','register','article','assessment','tracker','metadata','thumbnail','reference','script','talking_points','reading','document'}
PLATFORMS={'YouTube','Instagram','TikTok','X','Threads'}
METRICS={'views','likes','comments','shares','saves','watch_minutes','followers_gained','followers_lost'}

def create_app(data_dir=None,testing=False):
    store=Store(data_dir)
    config_path=store.path/'config.json'
    config=json.loads(config_path.read_text(encoding='utf-8')) if config_path.exists() else {}
    if not config.get('secret') or not config.get('password_hash'):
        raise RuntimeError('Run python manage.py init before starting the app.')
    app=Flask(__name__,static_folder='static')
    app.config.update(SECRET_KEY=config['secret'],MAX_CONTENT_LENGTH=26*1024*1024,MAX_FORM_MEMORY_SIZE=2*1024*1024,
        SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',SESSION_COOKIE_SECURE=config.get('secure_cookie',False),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),TRUSTED_HOSTS=config.get('hosts',['localhost','127.0.0.1']),TESTING=testing)
    app.store=store
    store.recover_interrupted()
    executor=ThreadPoolExecutor(max_workers=1)
    failures={}; login_lock=threading.Lock()

    @app.before_request
    def security():
        # The server itself binds loopback. For phone access the supplied Caddy proxy
        # enforces a private CIDR allowlist and TLS; forwarded headers are not trusted.
        if request.path.startswith('/api/'):
            if request.method not in ('GET','HEAD','OPTIONS'):
                origin=request.headers.get('Origin')
                expected_origin=config.get('origin','http://127.0.0.1:8765')
                allowed_origins={expected_origin,'http://127.0.0.1:8765','http://localhost:8765'}
                if origin and origin not in allowed_origins: abort(403,description='Origin rejected')
                if request.headers.get('Sec-Fetch-Site')=='cross-site': abort(403,description='Cross-site request rejected')
                if request.path!='/api/login' and (not session.get('csrf') or not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),session['csrf'])):
                    abort(403,description='Session expired or CSRF check failed. Reload and sign in.')
            if request.path not in ('/api/login','/api/session') and not session.get('authenticated'):
                abort(401,description='Sign in to continue')

    @app.after_request
    def headers(response):
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Cache-Control']='no-store'
        return response

    @app.errorhandler(Exception)
    def errors(error):
        if isinstance(error,HTTPException): return jsonify(error=error.description),error.code
        if isinstance(error,(ValueError,UnicodeError,KeyError)): return jsonify(error=str(error)),400
        # Do not leak credentials, transcript content, paths or stack traces to LAN clients.
        if testing: raise error
        return jsonify(error='Operation failed. Your saved data is retained. Check the local service log.'),500

    @app.get('/')
    def index(): return app.send_static_file('index.html')
    @app.get('/api/session')
    def who(): return jsonify(authenticated=bool(session.get('authenticated')),csrf=session.get('csrf',''))
    @app.post('/api/login')
    def login():
        if not request.is_json: abort(415)
        password=request.json.get('password','')
        if not isinstance(password,str) or len(password)>512: abort(400)
        # Global throttling prevents bypass through spoofed forwarded IPs.
        with login_lock:
            recent=[t for t in failures.get('global',[]) if time.time()-t<900]
            if len(recent)>=8: abort(429,description='Too many attempts. Try again in 15 minutes.')
            if not check_password_hash(config['password_hash'],password):
                recent.append(time.time()); failures['global']=recent; abort(401,description='Incorrect password')
            failures.clear()
        session.clear(); session.permanent=True; session['authenticated']=True; session['csrf']=secrets.token_urlsafe(32)
        return jsonify(csrf=session['csrf'])
    @app.post('/api/logout')
    def logout(): session.clear(); return jsonify(ok=True)
    @app.get('/api/state')
    def state():
        return jsonify(files=store.files(),ideas=store.entities('idea'),drafts=store.entities('draft'),posts=store.entities('post'),jobs=store.jobs(),
            preferences=store.get('preferences'),connections=connections(),api_configured=bool(os.environ.get('OPENAI_API_KEY')),kinds=KINDS,
            description=get_profile(store)['description'],profile=get_profile(store),version=VERSION,network='TLS private proxy' if config.get('secure_cookie') else 'Loopback only')
    @app.get('/license')
    def license_text():
        return send_file(ROOT/'LICENSE',mimetype='text/plain')
    @app.get('/source')
    def source_download():
        return send_file(io.BytesIO(build_source_archive(ROOT)),as_attachment=True,
                         download_name='mystical-mark-studio-'+VERSION+'-source.zip',mimetype='application/zip')
    @app.post('/api/profile')
    def save_profile():
        store.set('creator_profile',validate_profile(request.get_json()))
        return jsonify(ok=True)
    @app.post('/api/preferences')
    def preferences():
        b=request.get_json()
        if b.get('mode') not in ('work','api'): raise ValueError('Invalid mode')
        if b.get('effort') not in ('low','medium','high','xhigh','max'): raise ValueError('Invalid reasoning effort')
        for k in ('model','image_model'):
            if not re.fullmatch(r'[a-zA-Z0-9._-]{1,100}',b.get(k,'')): raise ValueError('Invalid model name')
        store.set('preferences',{k:b[k] for k in ('mode','model','effort','image_model')}); return jsonify(ok=True)
    @app.get('/api/models')
    def models():
        if store.get('preferences',{}).get('mode')!='api': raise ValueError('Model discovery is available only in explicit API mode. Select the model yourself in ChatGPT Work.')
        key=os.environ.get('OPENAI_API_KEY')
        if not key: raise ValueError('OPENAI_API_KEY is not configured')
        data=request_json('https://api.openai.com/v1/models',None,key)
        return jsonify(models=sorted(x['id'] for x in data.get('data',[]) if x['id'].startswith(('gpt-','o3','o4'))))

    @app.post('/api/files')
    def upload():
        f=request.files.get('file')
        if not f or not f.filename: raise ValueError('Choose a file')
        suffix=Path(f.filename).suffix.lower()
        if suffix not in ('.txt','.md','.json','.csv','.srt','.vtt','.png','.jpg','.jpeg','.webp','.pdf'): raise ValueError('Unsupported file type')
        raw=f.read()
        if len(raw)>25*1024*1024: abort(413)
        if suffix in ('.png','.jpg','.jpeg','.webp'):
            from PIL import Image
            with Image.open(io.BytesIO(raw)) as im:
                if im.width*im.height>40_000_000: raise ValueError('Image exceeds 40 megapixels')
                im.verify()
        elif suffix!='.pdf': raw.decode('utf-8-sig')
        kind=request.form.get('kind','document')
        if kind not in ALLOWED_KINDS: raise ValueError('Invalid file type')
        id_=store.add_file(f.filename,raw,kind,request.form.get('project','')[:200],request.form.get('tags','')[:500],request.form.get('private')=='true')
        return jsonify(id=id_)
    @app.get('/api/files/<id_>/download')
    def download(id_):
        f=store.file(id_)
        return send_file(io.BytesIO(store.bytes(id_)),as_attachment=True,download_name=f['name'],mimetype='application/octet-stream')
    @app.get('/api/files/<id_>/preview')
    def preview(id_):
        f=store.file(id_); ext=Path(f['name']).suffix.lower()
        if ext in ('.png','.jpg','.jpeg','.webp'):
            return send_file(io.BytesIO(store.bytes(id_)),mimetype=mimetypes.guess_type(f['name'])[0])
        if ext=='.pdf': raise ValueError('Download PDFs to view them')
        return jsonify(text=store.bytes(id_).decode('utf-8-sig'))
    @app.post('/api/files/<id_>/edit')
    def edit_file(id_):
        store.file(id_); b=request.json
        if b.get('kind') not in ALLOWED_KINDS: raise ValueError('Invalid category')
        with store.connect() as db:
            db.execute('UPDATE files SET project=?,tags=?,kind=?,archived=?,private=? WHERE id=?',
                (str(b.get('project',''))[:200],str(b.get('tags',''))[:500],b['kind'],int(bool(b.get('archived'))),int(bool(b.get('private'))),id_))
        return jsonify(ok=True)
    @app.post('/api/files/<id_>/delete')
    def delete_file(id_):
        store.file(id_)
        if request.json.get('confirm')!='DELETE': raise ValueError('Type DELETE to permanently remove the local file')
        # Preserve provenance for in-flight tasks. Completed jobs retain hashes and prompt snapshots.
        for job in store.jobs():
            if job['state'] in ('waiting_work','queued','running') and id_ in job['body'].get('file_ids',[]): raise ValueError('This file is used by an active job. Complete or cancel that job first.')
        backup=store.backup()
        with LOCK:
            with store.connect() as db: db.execute('DELETE FROM files WHERE id=?',(id_,))
            (store.path/'blobs'/id_).unlink(missing_ok=True)
        return jsonify(ok=True,backup=backup.name,note='A local safety backup still contains this file. Remove that backup separately if reclaiming space.')

    @app.post('/api/entities/<type_>')
    def save_entity(type_):
        b=request.json; id_=b.pop('id',None)
        if type_=='idea':
            if not str(b.get('title','')).strip(): raise ValueError('A title is required')
            if b.get('status','idea') not in ('idea','selected','recorded','used','declined'): raise ValueError('Invalid idea status')
            b['rating']=int(b.get('rating',0))
            if not 0<=b['rating']<=5: raise ValueError('Rating must be 0–5')
        elif type_=='draft':
            if b.get('format') not in ('short','long','reading'): raise ValueError('Invalid draft format')
            if not str(b.get('title','')).strip(): raise ValueError('A title is required')
            if len(str(b.get('content','')))>2_000_000: raise ValueError('Draft is too large')
        else: raise ValueError('Invalid record type')
        if id_ and store.entity(id_)['type']!=type_: raise ValueError('Invalid record')
        b={k:v for k,v in b.items() if k not in ('created','updated','type')}
        return jsonify(id=store.entity_save(type_,b,id_))
    @app.get('/api/drafts/<id_>/revisions')
    def revisions(id_): return jsonify(revisions=[x for x in store.entities('revision') if x.get('draft_id')==id_])
    @app.post('/api/drafts/<id_>/export')
    def export_draft(id_):
        d=store.entity(id_)
        if d['type']!='draft': raise ValueError('Not a draft')
        return jsonify(id=store.add_file(d['title']+'.md',d.get('content',''),'script' if d['format']=='short' else ('reading' if d['format']=='reading' else 'talking_points'),d['title'],private=d['format']=='reading'))
    @app.post('/api/pdf')
    def pdf():
        b=request.json
        if not b.get('reviewed'): raise ValueError('Review the summary before making the client PDF')
        if b.get('file_id'):
            f=store.file(b['file_id']); text=store.bytes(f['id']).decode('utf-8-sig'); title=b.get('title') or f['name']
        else: text=str(b.get('text','')); title=str(b.get('title','Your reading'))
        if not text.strip() or len(text)>200000: raise ValueError('Provide a summary under 200,000 characters')
        id_=store.add_file(title+'.pdf',make_pdf(title,text),'reading',str(b.get('project',title)),private=True)
        return jsonify(id=id_)
    @app.post('/api/split')
    def split(): return jsonify(parts=split_posts(str(request.json.get('text','')),request.json.get('platform')))

    def get_job(id_):
        job=next((j for j in store.jobs() if j['id']==id_),None)
        if not job: raise ValueError('Job not found')
        return job
    def worker(id_):
        store.update_job(id_,'running')
        try: run_api(store,get_job(id_))
        except Exception as e:
            store.update_job(id_,'failed',error=str(e) if isinstance(e,(ValueError,ProviderError)) else 'Generation failed. Existing outputs remain saved. Check your provider dashboard before retrying.')
    @app.post('/api/jobs')
    def create_job():
        b=request.json; kind=b.get('kind')
        prompt,images=build_prompt(store,kind,b)
        b={k:b.get(k) for k in ('file_ids','title','topic','video_url','period_start','period_end','recorded_at','release_at','cutoff','notes','register','include_private')}
        b['file_ids']=b.get('file_ids') or []; b['prompt']=prompt
        prefs=store.get('preferences',{})
        state='waiting_work'
        if prefs.get('mode')=='api':
            if not request.json.get('api_confirmed'): raise ValueError('Confirm this request sends selected data to the separately billed OpenAI API.')
            if not os.environ.get('OPENAI_API_KEY'): raise ValueError('Set OPENAI_API_KEY in the private service environment first.')
            state='queued'
        b['provider']=prefs.get('mode','work'); b['model']=prefs.get('model'); b['effort']=prefs.get('effort'); b['image_model']=prefs.get('image_model')
        id_=store.new_job(kind,b.get('title') or KINDS[kind],b,state)
        if state=='queued': executor.submit(worker,id_)
        return jsonify(id=id_)
    @app.get('/api/jobs/<id_>/packet')
    def get_packet(id_):
        job=get_job(id_)
        return send_file(io.BytesIO(packet(store,job)),download_name='Mystical_Mark_Work_'+id_[:8]+'.zip',as_attachment=True,mimetype='application/zip')
    @app.post('/api/jobs/<id_>/import')
    def import_job(id_):
        job=get_job(id_)
        if job['state'] in ('running','queued'): raise ValueError('Wait for the active generation to finish')
        result=import_result(store,job,request.json)
        previous=job.get('result',{})
        result['file_ids']=previous.get('file_ids',[])+result['file_ids']
        result['idea_ids']=previous.get('idea_ids',[])+result['idea_ids']
        store.update_job(id_,'imported',result)
        return jsonify(**result)
    @app.post('/api/jobs/<id_>/attach')
    def attach_job(id_):
        job=get_job(id_); f=store.file(request.json['file_id'])
        if job['kind']=='reading' or any(store.file(i)['private'] for i in job['body'].get('file_ids',[]) if any(x['id']==i for x in store.files())):
            with store.connect() as db: db.execute('UPDATE files SET private=1 WHERE id=?',(f['id'],))
        result=job['result']; result.setdefault('file_ids',[])
        if f['id'] not in result['file_ids']: result['file_ids'].append(f['id'])
        store.update_job(id_,job['state'],result)
        return jsonify(ok=True)
    @app.post('/api/jobs/<id_>/complete')
    def complete_job(id_):
        job=get_job(id_)
        if job['state'] in ('queued','running'): raise ValueError('Active API jobs cannot be manually completed')
        if request.json.get('cancel'): store.update_job(id_,'cancelled'); return jsonify(ok=True)
        if not job['result'].get('file_ids') and not job['result'].get('idea_ids'): raise ValueError('Import or attach outputs first')
        result=job['result']; result['review']='Reviewed by the creator on '+now()
        store.update_job(id_,'reviewed',result); return jsonify(ok=True)

    @app.post('/api/posts')
    def save_post():
        b=request.json; platform=b.get('platform'); parts=b.get('parts',[])
        if platform not in ('X','Threads') or not isinstance(parts,list) or not 1<=len(parts)<=100: raise ValueError('Invalid post')
        for p in parts:
            if not isinstance(p,str) or len(split_posts(p,platform))!=1: raise ValueError('A post exceeds the conservative length limit')
        state=b.get('state','draft')
        if state not in ('draft','approved','scheduled'): raise ValueError('Invalid publishing state')
        if state!='draft' and not b.get('reviewed'): raise ValueError('Review the exact post text before approving it')
        if state=='scheduled':
            when=datetime.fromisoformat(b.get('scheduled_at',''))
            if not when.tzinfo or when<=datetime.now(timezone.utc): raise ValueError('Choose a future date and time with a timezone')
            if not connections().get(platform): raise ValueError('Configure platform credentials before scheduling')
        body={'title':str(b.get('title','Social post'))[:300],'platform':platform,'parts':parts,'state':state,
            'scheduled_at':b.get('scheduled_at',''),'approved_at':now() if state!='draft' else '', 'remote_ids':[]}
        with __import__('publishing').PUBLISH_LOCK:
            id_=b.get('id')
            if id_:
                old=store.entity(id_)
                if old['type']!='post' or old.get('state') not in ('draft','approved','scheduled','overdue','blocked'):
                    raise ValueError('Published or uncertain posts cannot be rewritten; check the platform first.')
            return jsonify(id=store.entity_save('post',body,id_))
    @app.post('/api/posts/<id_>/publish')
    def publish_now(id_): return jsonify(post=publish(store,id_))
    @app.post('/api/posts/<id_>/cancel')
    def cancel_post(id_):
        with __import__('publishing').PUBLISH_LOCK:
            post=store.entity(id_)
            if post['type']!='post' or post.get('state') not in ('draft','approved','scheduled','overdue','blocked'): raise ValueError('This post cannot be cancelled locally')
            post['state']='cancelled'; store.entity_save('post',{k:v for k,v in post.items() if k not in ('id','type')},id_)
        return jsonify(ok=True)

    @app.get('/api/analytics')
    def analytics():
        with store.connect() as db: rows=[dict(r) for r in db.execute('SELECT * FROM metrics ORDER BY date DESC')]
        return jsonify(rows=rows)
    @app.post('/api/analytics/import')
    def metrics_import():
        b=request.json; text=str(b.get('csv',''))
        if len(text)>5_000_000: raise ValueError('CSV too large')
        reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
        required={'platform','account','content_id','date','metric','value','basis'}
        if not required.issubset(set(reader.fieldnames or [])): raise ValueError('Use the provided CSV schema: platform,account,content_id,date,metric,value,basis')
        records=[]
        for r in reader:
            if len(records)>=50000: raise ValueError('CSV exceeds 50,000 rows')
            if r['platform'] not in PLATFORMS or r['metric'] not in METRICS or r['basis'] not in ('daily','lifetime_snapshot'): raise ValueError('Invalid platform, metric or basis in CSV')
            datetime.strptime(r['date'],'%Y-%m-%d')
            val=float(r['value'])
            import math
            if not math.isfinite(val) or val<0: raise ValueError('Metrics must be finite non-negative numbers')
            if not r['account'].strip(): raise ValueError('Each metric needs an account')
            from storage import uid
            records.append((uid(),r['platform'],r['account'],r['content_id'],r['date'],r['metric'],val,r['basis']))
        with store.connect() as db:
            db.executemany('INSERT INTO metrics VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(platform,account,content_id,date,metric,basis) DO UPDATE SET value=excluded.value',records)
        return jsonify(imported=len(records))
    @app.get('/api/analytics/export')
    def metrics_export():
        with store.connect() as db: rows=[dict(r) for r in db.execute('SELECT platform,account,content_id,date,metric,value,basis FROM metrics ORDER BY date')]
        out=io.StringIO(); writer=csv.DictWriter(out,fieldnames=['platform','account','content_id','date','metric','value','basis']); writer.writeheader(); writer.writerows(rows)
        return send_file(io.BytesIO(out.getvalue().encode()),download_name='Mystical_Mark_Analytics.csv',as_attachment=True,mimetype='text/csv')
    @app.post('/api/analytics/handoff')
    def analytics_handoff():
        with store.connect() as db: rows=[dict(r) for r in db.execute('SELECT platform,account,content_id,date,metric,value,basis FROM metrics ORDER BY date')]
        content='# Analytics review for ChatGPT Work\n\nAnalyse these imported observations. Separate platforms and daily counts from lifetime snapshots. Deduplicate snapshots; do not add account-level rows to their post-level components. Cross-platform totals are activity, not unique people. Compare only equivalent windows and definitions. Identify evidence limits, useful experiments and content opportunities; never invent missing metrics.\n\n```json\n'+json.dumps(rows,indent=2)+'\n```'
        return jsonify(id=store.add_file('Analytics_Work_Handoff.md',content,'document'))
    @app.post('/api/backup')
    def backup():
        p=store.backup()
        return send_file(p,download_name=p.name,as_attachment=True,mimetype='application/zip')
    @app.get('/api/export')
    def export_records():
        return send_file(io.BytesIO(json.dumps({'ideas':store.entities('idea'),'drafts':store.entities('draft'),'posts':store.entities('post')},ensure_ascii=False,indent=2).encode()),download_name='Mystical_Mark_Records.json',as_attachment=True,mimetype='application/json')
    return app

def main():
    from waitress import serve
    app=create_app()
    stop=threading.Event()
    def scheduler():
        while not stop.wait(20):
            try: tick(app.store)
            except Exception: pass  # Never log client content or provider credentials.
    threading.Thread(target=scheduler,daemon=True).start()
    # Fixed loopback binding. Remote access must go through the supplied private TLS proxy.
    serve(app,host='127.0.0.1',port=8765,threads=8,max_request_body_size=26*1024*1024,channel_timeout=120)

if __name__=='__main__': main()

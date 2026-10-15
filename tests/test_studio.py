# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Mystical Mark Studio contributors
# Distributed WITHOUT ANY WARRANTY. See LICENSE and NOTICE.
import io,json,os,sys,tempfile,unittest,zipfile,sqlite3
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from werkzeug.security import generate_password_hash
from storage import Store, ROOT
from app import create_app
from workflows import build_prompt, split_posts
from studio_profile import get_profile
DESCRIPTION="Synthetic creator description for tests."
from ai import import_result, parse_result, run_api
from pdf_export import make_pdf

SRT='1\n00:00:00,000 --> 00:00:12,000\nThis week may bring a public discussion.\n\n2\n00:00:12,000 --> 00:00:30,000\nThe outcome remains uncertain.\n'
class StudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.hash=generate_password_hash('a-long-test-passphrase',method='scrypt')
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)
        self.store=Store(self.path)
        profile=get_profile(self.store);profile["description"]=DESCRIPTION;self.store.set("creator_profile",profile)
        self.store.entity_save("idea",{"title":"Synthetic idea","notes":"Test notes","status":"idea","rating":0},"fixture-idea")
        (self.path/'config.json').write_text(json.dumps({'secret':'test-secret','password_hash':self.hash,'hosts':['localhost','127.0.0.1']}))
        self.app=create_app(self.path,testing=True);self.c=self.app.test_client()
        self.csrf=self.c.post('/api/login',json={'password':'a-long-test-passphrase'}).json['csrf']
    def tearDown(self): self.tmp.cleanup()
    def post(self,path,data): return self.c.post('/api/'+path,json=data,headers={'X-CSRF-Token':self.csrf})
    def transcript(self,private=False):return self.store.add_file('week.srt',SRT,'transcript',private=private)
    def test_fresh_store_contains_only_test_fixture(self):
        ideas=self.store.entities('idea');self.assertEqual(len(ideas),1);self.assertEqual(ideas[0]['title'],'Synthetic idea')
    def test_seed_does_not_overwrite_edits(self):
        i=self.store.entities('idea')[0];self.store.entity_save('idea',{'title':'My edit','status':'used','rating':5},i['id']);Store(self.path)
        self.assertEqual(self.store.entity(i['id'])['title'],'My edit')
    def test_auth_and_csrf(self):
        other=self.app.test_client();self.assertEqual(other.get('/api/state').status_code,401)
        self.assertEqual(self.c.post('/api/preferences',json={}).status_code,403)
        self.assertEqual(self.c.post('/api/logout',json={},headers={'X-CSRF-Token':self.csrf,'Origin':'https://evil.example'}).status_code,403)
    def test_rebinding_host_rejected(self):self.assertEqual(self.c.get('/api/session',headers={'Host':'evil.example'}).status_code,400)
    def test_security_headers(self):
        r=self.c.get('/');self.assertIn("frame-ancestors 'none'",r.headers['Content-Security-Policy']);self.assertEqual(r.headers['Cache-Control'],'no-store');r.close()
    def test_private_sources_require_choice(self):
        id_=self.transcript(True);r=self.post('jobs',{'kind':'reading','file_ids':[id_]});self.assertEqual(r.status_code,400)
        r=self.post('jobs',{'kind':'reading','file_ids':[id_],'include_private':True});self.assertEqual(r.status_code,200)
    def test_upload_and_download(self):
        r=self.c.post('/api/files',data={'file':(io.BytesIO(SRT.encode()),'../../week.srt'),'kind':'transcript'},headers={'X-CSRF-Token':self.csrf});self.assertEqual(r.status_code,200)
        f=self.store.file(r.json['id']);self.assertNotIn('/',f['name']);self.assertEqual(self.c.get('/api/files/'+f['id']+'/download').data,SRT.encode())
    def test_work_packet_and_frozen_prompt(self):
        id_=self.transcript();r=self.post('jobs',{'kind':'long','title':'Test','file_ids':[id_],'register':True});job=self.store.jobs()[0]
        self.assertEqual(job['state'],'waiting_work');self.assertIn(DESCRIPTION,job['body']['prompt']);self.assertIn('Workflow version 1.1',job['body']['prompt'])
        data=self.c.get('/api/jobs/'+r.json['id']+'/packet').data
        with zipfile.ZipFile(io.BytesIO(data)) as z:self.assertEqual(z.read('TASK.md').decode(),job['body']['prompt'])
    def test_monthly_and_yearly_rules(self):
        f=self.store.add_file('baseline.md','# Registered criteria','register')
        prompt,_=build_prompt(self.store,'monthly',{'file_ids':[f]});self.assertIn('Do not create or update it in weekly mode',prompt)
        prompt,_=build_prompt(self.store,'yearly',{'file_ids':[f]});self.assertIn('Do not replace or extend the monthly carry-forward tracker',prompt)
    def test_import_keeps_register_immutable(self):
        id_=self.transcript();j=self.post('jobs',{'kind':'register','file_ids':[id_]}).json['id']
        for content in ('# Original','# Revised'):
            self.assertEqual(self.post('jobs/'+j+'/import',{'files':[{'name':'register.md','kind':'register','content':content}]}).status_code,200)
        fs=[f for f in self.store.files() if f['kind']=='register'];self.assertEqual(len(fs),2);self.assertEqual({self.store.bytes(f['id']).decode() for f in fs},{'# Original','# Revised'})
    def test_description_insert_exact(self):
        meta={'title':'Forecast','description_intro':'A description','chapters':[{'time':'00:00','title':'Opening'}],'hashtags':['#a','#b','#c','#d','#e']}
        job={'kind':'long','title':'Forecast','body':{'file_ids':[]}}
        result=import_result(self.store,job,{'files':[{'name':'youtube_metadata.json','kind':'metadata','content':json.dumps(meta)}]})
        content=json.loads(self.store.bytes(result['file_ids'][-1]));self.assertIn(DESCRIPTION,content['description']);self.assertEqual(content['description'].count(DESCRIPTION),1)
    def test_private_outputs_stay_private(self):
        id_=self.transcript(True);job={'kind':'reading','title':'Client','body':{'file_ids':[id_]}}
        r=import_result(self.store,job,{'files':[{'name':'summary.md','content':'Private guidance'}]});self.assertTrue(self.store.file(r['file_ids'][0])['private'])
    def test_import_rejects_executables(self):
        with self.assertRaises(ValueError):parse_result({'files':[{'name':'../../bad.html','content':'<script>alert(1)</script>'}]})
    def test_draft_revisions(self):
        id_=self.post('entities/draft',{'title':'Script','format':'short','content':'First'}).json['id']
        self.post('entities/draft',{'id':id_,'title':'Script','format':'short','content':'Second'})
        r=self.c.get('/api/drafts/'+id_+'/revisions').json;self.assertEqual(r['revisions'][0]['body']['content'],'First')
    def test_split_preserves_all_words_unicode(self):
        text=('Guidance 💜 for queer people.\n\n'*80)+'https://example.org'
        for platform in ('X','Threads'):
            parts=split_posts(text,platform);self.assertEqual(' '.join(parts).split(),text.split());self.assertGreater(len(parts),1)
    def test_split_rejects_long_word_without_dropping(self):
        with self.assertRaises(ValueError):split_posts('a'*600,'Threads')
    def test_backup_consistent(self):
        id_=self.transcript();archive=self.store.backup()
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(z.read('blobs/'+id_),SRT.encode());self.assertNotIn('config.json',z.namelist());self.assertNotIn('secrets.env',z.namelist())
            path=self.path/'check.sqlite';path.write_bytes(z.read('studio.sqlite3'));db=sqlite3.connect(path);self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok');db.close()
    def test_metrics_upsert_and_atomic_invalid(self):
        header='platform,account,content_id,date,metric,value,basis\n'
        for v in (100,200):self.assertEqual(self.post('analytics/import',{'csv':header+f'YouTube,mark,v1,2026-10-01,views,{v},daily\n'}).status_code,200)
        rows=self.c.get('/api/analytics').json['rows'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['value'],200)
        self.assertEqual(self.post('analytics/import',{'csv':header+'X,mark,x1,2026-10-01,views,3,daily\nTikTok,mark,t1,2026-10-01,views,NaN,daily\n'}).status_code,400)
        self.assertEqual(len(self.c.get('/api/analytics').json['rows']),1)
    def test_publish_requires_approval(self):
        self.assertEqual(self.post('posts',{'platform':'X','parts':['Test'],'state':'approved'}).status_code,400)
        id_=self.post('posts',{'platform':'X','parts':['Test'],'state':'draft'}).json['id'];self.assertEqual(self.post('posts/'+id_+'/publish',{}).status_code,400)
    def test_no_blind_publication_retry(self):
        id_=self.post('posts',{'platform':'X','parts':['One','Two'],'state':'approved','reviewed':True}).json['id']
        with patch.dict(os.environ,{'X_USER_ACCESS_TOKEN':'fake'}),patch('publishing.request_json',side_effect=[{'data':{'id':'remote1'}},OSError('timeout')]):
            r=self.post('posts/'+id_+'/publish',{});self.assertEqual(r.json['post']['state'],'uncertain');self.assertEqual(r.json['post']['remote_ids'],['remote1']);self.assertEqual(self.post('posts/'+id_+'/publish',{}).status_code,400)
    def test_api_requires_explicit_opt_in(self):
        self.store.set('preferences',{'mode':'api','model':'gpt-6-astra','effort':'medium','image_model':'test'})
        self.assertEqual(self.post('jobs',{'kind':'long','file_ids':[self.transcript()]}).status_code,400)
    def test_api_stub_stores_outputs(self):
        self.store.set('preferences',{'mode':'api','model':'gpt-6-astra','effort':'medium'})
        body={'prompt':'Test','file_ids':[]};id_=self.store.new_job('short','Test',body,'queued');job=self.store.jobs()[0]
        data={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'files':[{'name':'short.md','content':'Short metadata'}]})}]}]}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'fake'}),patch('ai.request_json',return_value=data):run_api(self.store,job)
        self.assertEqual(self.store.jobs()[0]['state'],'completed')
    def test_research_rejects_absent_search(self):
        self.store.set('preferences',{'mode':'api','model':'gpt-6-astra','effort':'medium'})
        id_=self.store.new_job('weekly','Review',{'prompt':'Test','file_ids':[]},'queued')
        with patch.dict(os.environ,{'OPENAI_API_KEY':'fake'}),patch('ai.request_json',return_value={'status':'completed','output':[]}):
            with self.assertRaises(Exception):run_api(self.store,self.store.jobs()[0])
    def test_pdf_handles_long_wrapped_content(self):
        pdf=make_pdf('Reading reference','# Core takeaway\n\nThis is a faithful summary.\n\n## Guidance\n\n'+('A longer reflection with <literal HTML> and & symbols. '*200))
        self.assertTrue(pdf.startswith(b'%PDF'))
    def test_restore_preserves_data_and_disarms_schedules(self):
        from manage import restore
        from types import SimpleNamespace
        id_=self.transcript()
        post=self.store.entity_save('post',{'title':'Future post','platform':'X','parts':['Hi'],'state':'scheduled','scheduled_at':'2030-01-01T00:00:00+00:00','approved_at':'then','remote_ids':[]})
        archive=self.store.backup()
        self.store.entity_save('idea',{'title':'Added after backup'},'newer')
        with patch.dict(os.environ,{'MM_DATA_DIR':str(self.path)}),patch('builtins.input',return_value='RESTORE'),patch('manage.subprocess.run',return_value=SimpleNamespace(returncode=0)):
            restore(archive)
        restored=Store(self.path)
        self.assertEqual(restored.bytes(id_),SRT.encode())
        self.assertEqual(restored.entity(post)['state'],'draft')
        with self.assertRaises(ValueError):restored.entity('newer')
        self.assertTrue((self.path/'config.json').exists())
    def test_restore_rejects_archive_traversal(self):
        from manage import restore
        bad=self.path/'bad.zip'
        with zipfile.ZipFile(bad,'w') as z:z.writestr('../escape','no')
        with patch.dict(os.environ,{'MM_DATA_DIR':str(self.path)}):
            with self.assertRaises(ValueError):restore(bad)
        self.assertEqual(len(self.store.entities('idea')),1)
    def test_update_saved_post_and_lock_uncertain(self):
        id_=self.post('posts',{'platform':'X','parts':['Old'],'state':'draft'}).json['id']
        self.assertEqual(self.post('posts',{'id':id_,'platform':'X','parts':['New'],'state':'approved','reviewed':True}).json['id'],id_)
        self.assertEqual(len(self.store.entities('post')),1)
        self.store.entity_save('post',{'state':'uncertain','platform':'X','parts':['New']},id_)
        self.assertEqual(self.post('posts',{'id':id_,'platform':'X','parts':['Overwrite'],'state':'draft'}).status_code,400)
    def test_backup_does_not_interrupt_running_jobs(self):
        id_=self.store.new_job('short','Running',{},'running')
        other=Store(self.path);other.backup()
        self.assertEqual(self.store.jobs()[0]['state'],'running')
    def test_period_validation(self):
        with self.assertRaises(ValueError):build_prompt(self.store,'register',{'file_ids':[self.transcript()],'period_start':'2026-10-10','period_end':'2026-10-01'})
    def test_newer_schema_refused(self):
        with self.store.connect() as db:db.execute('PRAGMA user_version=99')
        with self.assertRaises(RuntimeError):Store(self.path)
    def test_deleted_file_protected_in_active_job(self):
        id_=self.transcript();self.post('jobs',{'kind':'long','file_ids':[id_]})
        self.assertEqual(self.post('files/'+id_+'/delete',{'confirm':'DELETE'}).status_code,400)
if __name__=='__main__':unittest.main()

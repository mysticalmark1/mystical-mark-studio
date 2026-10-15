# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Mystical Mark Studio contributors
# Distributed WITHOUT ANY WARRANTY. See LICENSE and NOTICE.
import io, json, os, shutil, subprocess, sys, tempfile, unittest, zipfile, secrets
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from storage import Store, ROOT
from studio_profile import get_profile, migrate_legacy_profile, validate_profile
from source_bundle import build_source_archive
from app import create_app
import install
from run import load_credentials
from werkzeug.security import generate_password_hash


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.data=self.root/'data'
        self.store=Store(self.data)
    def tearDown(self): self.tmp.cleanup()
    def legacy(self):
        old=self.root/'previous';(old/'references').mkdir(parents=True,exist_ok=True)
        (old/'references/original-request.txt').write_text('--START DESCRIPTION INSERTION--\nPrivate description 💜\n--END DESCRIPTION INSERTION--',encoding='utf-8')
        (old/'references/advance-register.md').write_text('Private register instructions')
        (old/'references/assessment.md').write_text('Private assessment instructions')
        (old/'workflows.py').write_text("BRAND='Private creator voice'\nTHUMBNAIL='Private image guidance'\nZoneInfo('Europe/London')\nraise RuntimeError('Must never execute legacy code')\n")
        return old
    def test_profile_migration_preserves_content_and_is_idempotent(self):
        id_=self.store.entity_save('idea',{'title':'Edited existing idea','status':'used','rating':5},'original-1')
        file_=self.store.add_file('private.txt','Private content',private=True)
        config=b'{"secret":"synthetic","origin":"https://192.168.1.50:9443","secure_cookie":true}'
        (self.data/'config.json').write_bytes(config)
        self.assertTrue(migrate_legacy_profile(self.store,self.legacy()))
        profile=get_profile(self.store);self.assertEqual(profile['description'],'Private description 💜');self.assertEqual(profile['timezone'],'Europe/London')
        self.assertEqual(self.store.entity(id_)['status'],'used');self.assertEqual(self.store.bytes(file_),b'Private content')
        self.assertEqual((self.data/'config.json').read_bytes(),config)
        profile['description']='New edit';self.store.set('creator_profile',profile)
        self.assertFalse(migrate_legacy_profile(self.store,self.root/'previous'));self.assertEqual(get_profile(self.store)['description'],'New edit')
    def test_new_install_has_no_private_seed(self):
        self.assertEqual(self.store.entities('idea'),[])
        self.assertEqual(get_profile(self.store)['description'],'')
        self.assertEqual(get_profile(self.store)['timezone'],'UTC')
    def test_profile_validation(self):
        profile=get_profile(self.store);profile['timezone']='Not/AZone'
        with self.assertRaises(ValueError):validate_profile(profile)
    def test_source_excludes_unknown_files_and_private_state(self):
        sentinel=secrets.token_hex(32)
        code=self.root/'code';shutil.copytree(ROOT,code,ignore=shutil.ignore_patterns('__pycache__','.venv'))
        for name in ['config.json','secrets.env','studio.sqlite3','private-profile.md']:(code/name).write_text(sentinel)
        (code/'private').mkdir();(code/'private'/'notes.py').write_text(sentinel)
        with zipfile.ZipFile(io.BytesIO(build_source_archive(code))) as z:
            self.assertIn('mystical-mark-studio/LICENSE',z.namelist())
            for name in z.namelist():self.assertNotIn(sentinel.encode(),z.read(name))
    def test_manifest_rejects_traversal(self):
        (self.root/'SOURCE_FILES.txt').write_text('../secret.txt\n')
        with self.assertRaises(ValueError):build_source_archive(self.root)
    def test_source_and_license_available_without_login(self):
        (self.data/'config.json').write_text(json.dumps({'secret':'synthetic','password_hash':generate_password_hash('synthetic-test-passphrase')}))
        client=create_app(self.data,testing=True).test_client()
        self.assertEqual(client.get('/api/state').status_code,401)
        for url in ['/source','/license']:
            response=client.get(url);self.assertEqual(response.status_code,200);response.close()
    def test_private_profile_api_requires_auth_csrf_and_is_used(self):
        (self.data/'config.json').write_text(json.dumps({'secret':'synthetic','password_hash':generate_password_hash('synthetic-test-passphrase')}))
        client=create_app(self.data,testing=True).test_client();profile=get_profile(self.store);profile['description']='Private inserted text'
        self.assertEqual(client.post('/api/profile',json=profile).status_code,403)
        token=client.post('/api/login',json={'password':'synthetic-test-passphrase'}).json['csrf']
        self.assertEqual(client.post('/api/profile',json=profile,headers={'X-CSRF-Token':token}).status_code,200)
        f=self.store.add_file('transcript.txt','Synthetic words','transcript')
        from workflows import build_prompt
        self.assertIn('Private inserted text',build_prompt(self.store,'long',{'file_ids':[f]})[0])
    def test_snapshot_includes_secrets_and_excludes_older_backups(self):
        (self.data/'secrets.env').write_text('SYNTHETIC=sample')
        (self.data/'backups/old.zip').write_bytes(b'old')
        dest=self.data/'backups/pre-update-test';install.snapshot_data(self.data,dest)
        self.assertEqual((dest/'secrets.env').read_text(),'SYNTHETIC=sample')
        self.assertFalse((dest/'backups').exists());self.assertTrue((dest/'studio.sqlite3').exists())
    def test_existing_custom_data_path_and_unit_quoting(self):
        unit=self.root/'studio.service';custom=self.root/'custom data'
        unit.write_text(install.unit_text(self.root/'current',custom))
        self.assertEqual(install.installed_data_path(unit),custom)
        self.assertIn('WorkingDirectory='+str(self.root/'current'),unit.read_text())
        self.assertNotIn('WorkingDirectory="',unit.read_text());self.assertNotIn('EnvironmentFile="',unit.read_text())
    def test_portable_credentials_only_supported_keys(self):
        (self.data/'secrets.env').write_text('OPENAI_API_KEY=synthetic-file\nPATH=must-not-load\nTHREADS_USER_ID=123\n')
        with patch.dict(os.environ,{'MM_DATA_DIR':str(self.data),'OPENAI_API_KEY':'synthetic-env','PATH':'original'},clear=True):
            load_credentials();self.assertEqual(os.environ['PATH'],'original');self.assertEqual(os.environ['OPENAI_API_KEY'],'synthetic-env');self.assertEqual(os.environ['THREADS_USER_ID'],'123')


@unittest.skipUnless(sys.platform.startswith('linux'),'Linux installer transaction')
class InstallerTests(unittest.TestCase):
    def scenario(self,fail=False):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);base=home/'.local/lib/mystical-mark-studio';old=base/'releases/old';old.mkdir(parents=True)
            (old/'references').mkdir();(old/'references/original-request.txt').write_text('--START DESCRIPTION INSERTION--\nPrivate legacy block\n--END DESCRIPTION INSERTION--')
            (old/'references/advance-register.md').write_text('Private register');(old/'references/assessment.md').write_text('Private assessment')
            (old/'workflows.py').write_text("BRAND='Private brand'\nTHUMBNAIL='Private image'\nZoneInfo('UTC')")
            current=base/'current';current.symlink_to(old)
            data=home/'custom-data';store=Store(data);file_id=store.add_file('saved.txt','Synthetic saved file');idea=store.entity_save('idea',{'title':'Keep me','rating':4})
            config={'secret':'unchanged','password_hash':generate_password_hash('unchanged-passphrase'),'origin':'https://192.168.1.50:9443','secure_cookie':True,'hosts':['127.0.0.1','192.168.1.50']}
            (data/'config.json').write_text(json.dumps(config));(data/'secrets.env').write_text('OPENAI_API_KEY=synthetic')
            (data/'Caddyfile').write_text('SYNTHETIC GATEWAY')
            units=home/'.config/systemd/user';units.mkdir(parents=True);unit=units/'mystical-mark-studio.service';original=install.unit_text(current,data).replace('run.py','app.py');unit.write_text(original)
            gateway=units/'mystical-mark-https.service';gateway.write_text('SYNTHETIC HTTPS UNIT')
            calls=[]
            def fake_run(args,**kw):
                calls.append(args)
                if len(args)>2 and str(args[1]).endswith('manage.py'):
                    return subprocess.run([sys.executable,*map(str,args[1:])],check=True,**kw)
                if args[0]=='systemctl' and 'enable' in args and fail: raise RuntimeError('Injected activation failure')
                return subprocess.CompletedProcess(args,0)
            with patch('install.pathlib.Path.home',return_value=home),patch('install.os.geteuid',return_value=1000),patch('install.run',side_effect=fake_run),patch('install.subprocess.run',return_value=subprocess.CompletedProcess([],0)),patch.dict(os.environ,{},clear=False):
                # Real subprocess calls are not needed for migration here; run it directly with isolated env.
                def actual(args,**kw):
                    calls.append(args)
                    if len(args)>2 and str(args[1]).endswith('manage.py'):
                        if args[2]=='migrate-profile':migrate_legacy_profile(Store(data),old)
                        elif args[2]=='init':
                            from manage import init
                            with patch.dict(os.environ,{'MM_DATA_DIR':str(data)}):init()
                    if args[0]=='systemctl' and 'enable' in args and fail:raise RuntimeError('Injected activation failure')
                    return subprocess.CompletedProcess(args,0)
                with patch('install.run',side_effect=actual),patch.dict(os.environ,{'MM_DATA_DIR':str(data)}):
                    if fail:
                        with self.assertRaises(RuntimeError):install.main()
                    else:install.main()
            store=Store(data);self.assertEqual(store.bytes(file_id),b'Synthetic saved file');self.assertEqual(store.entity(idea)['rating'],4)
            self.assertEqual(json.loads((data/'config.json').read_text()),config);self.assertEqual((data/'secrets.env').read_text(),'OPENAI_API_KEY=synthetic')
            self.assertEqual((data/'Caddyfile').read_text(),'SYNTHETIC GATEWAY');self.assertEqual(gateway.read_text(),'SYNTHETIC HTTPS UNIT')
            self.assertEqual(get_profile(store)['description'],'Private legacy block');self.assertEqual(len(list((data/'backups').glob('pre-update-*'))),1)
            if fail:self.assertEqual(current.resolve(),old);self.assertEqual(unit.read_text(),original)
            else:self.assertNotEqual(current.resolve(),old)
    def test_update_preserves_data_login_credentials_gateway(self):self.scenario()
    def test_activation_failure_rolls_back_code_and_unit(self):self.scenario(True)

if __name__=='__main__':unittest.main()

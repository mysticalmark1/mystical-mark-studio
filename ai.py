# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Mystical Mark Studio contributors
# Distributed WITHOUT ANY WARRANTY. See LICENSE and NOTICE.
"""Optional explicitly enabled API transport. This is NOT ChatGPT Work."""
import base64, io, json, os, re, urllib.request, urllib.error
from PIL import Image, ImageOps
from studio_profile import get_profile

class ProviderError(Exception): pass

def request_json(url,payload,token,timeout=300):
    data=json.dumps(payload).encode() if payload is not None else None
    request=urllib.request.Request(url,data=data,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','User-Agent':'MysticalMarkStudio/1.1'})
    try:
        # Never allow auth-bearing redirects to arbitrary hosts.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs): return None
        with urllib.request.build_opener(NoRedirect).open(request,timeout=timeout) as r:
            raw=r.read(50*1024*1024+1)
            if len(raw)>50*1024*1024: raise ProviderError('Response exceeded the local limit.')
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        # Do not expose headers, credential-bearing URLs or private response bodies.
        raise ProviderError(f'Provider returned HTTP {e.code}. Check account access, quota, model and credentials. No automatic retry was attempted.') from None
    except (OSError,ValueError) as e:
        raise ProviderError('Connection or response failed. Check the provider dashboard before retrying; a timed-out request may still have incurred usage.') from None

def response_text(data):
    if data.get('status')!='completed': raise ProviderError('Generation did not complete. No partial output was accepted as complete.')
    return '\n'.join(c['text'] for item in data.get('output',[]) if item.get('type')=='message' for c in item.get('content',[]) if c.get('type')=='output_text')

def parse_result(value):
    if isinstance(value,str):
        value=value.strip()
        if value.startswith('```'): value=re.sub(r'^```(?:json)?\s*|\s*```$','',value)
        value=json.loads(value)
    if not isinstance(value,dict): raise ValueError('Expected an object with files and/or ideas')
    files=value.get('files',[]); ideas=value.get('ideas',[])
    if not isinstance(files,list) or len(files)>30 or not isinstance(ideas,list) or len(ideas)>200: raise ValueError('Too many or invalid results')
    for f in files:
        if not isinstance(f,dict) or not isinstance(f.get('content'),str) or len(f['content'])>2_000_000: raise ValueError('Each result file must have text content under 2 MB')
        name=f.get('name','')
        if not re.fullmatch(r'[\w .()\-]+\.(md|txt|json|csv|srt)',name,re.UNICODE): raise ValueError('Result names must be safe text-file names')
    for x in ideas:
        if not isinstance(x,dict) or not isinstance(x.get('title'),str) or not x['title'].strip(): raise ValueError('Each idea needs a title')
    if not files and not ideas: raise ValueError('No result files or ideas found')
    return files,ideas

def import_result(store,job,envelope):
    files,ideas=parse_result(envelope)
    ids=[]; idea_ids=[]
    private=job['kind']=='reading' or any(store.file(i)['private'] for i in job['body'].get('file_ids',[]))
    for f in files:
        kind=f.get('kind','document')
        if kind not in ('metadata','register','article','assessment','tracker','script','talking_points','reading','document'): kind='document'
        if f['name']=='youtube_metadata.json':
            meta=json.loads(f['content'])
            if not isinstance(meta,dict): raise ValueError('YouTube metadata must be a JSON object')
            hashtags=meta.get('hashtags',[])
            if not isinstance(hashtags,list) or len(hashtags)!=5 or not all(isinstance(x,str) and x.startswith('#') for x in hashtags): raise ValueError('YouTube metadata requires exactly five hashtags')
            chapters=meta.get('chapters',[])
            if not isinstance(chapters,list) or not all(isinstance(c,dict) and isinstance(c.get('time'),str) and isinstance(c.get('title'),str) for c in chapters): raise ValueError('Invalid chapters')
            if len(str(meta.get('title','')))>100: raise ValueError('YouTube title exceeds 100 characters')
            tags=meta.get('tags',[])
            if not isinstance(tags,list) or not all(isinstance(t,str) for t in tags) or len(','.join(tags))>500: raise ValueError('YouTube tags must be an array within 500 characters')
            intro=meta.get('description_intro','')
            if not isinstance(intro,str): raise ValueError('Invalid description intro')
            # Insertion is controlled here, never rewritten by the model.
            meta['description']=intro.strip()+'\n\n[Optional custom additions]\n\n'+get_profile(store)['description']+'\n\n'+'\n'.join(c['time']+' '+c['title'] for c in chapters)+'\n\n'+' '.join(hashtags)
            f={**f,'content':json.dumps(meta,ensure_ascii=False,indent=2)}
            ids.append(store.add_file('youtube_description.txt',meta['description'],'metadata',job['title'],private=private))
        ids.append(store.add_file(f['name'],f['content'],kind,job['title'],private=private))
    for idea in ideas:
        idea_ids.append(store.entity_save('idea',{'title':idea['title'][:300],'notes':str(idea.get('notes','')),'category':str(idea.get('category','')),'status':'idea','rating':0,'source':str(idea.get('source','Imported research'))}))
    return {'file_ids':ids,'idea_ids':idea_ids,'review':'Drafts · review before use'}

def run_api(store,job):
    prefs={**store.get('preferences',{}), **{k:job['body'][k] for k in ('model','effort','image_model') if job['body'].get(k)}}
    token=os.environ.get('OPENAI_API_KEY','')
    if prefs.get('mode')!='api' or not token: raise ProviderError('API mode is disabled or OPENAI_API_KEY is missing. Use the Work packet.')
    prompt=job['body']['prompt']
    research=job['kind'] in ('weekly','monthly','yearly','ideas','talking')
    payload={'model':prefs.get('model','gpt-6-astra'),'reasoning':{'effort':prefs.get('effort','medium')},'store':False,
        'input':prompt+'\nAPI transport: return only the result.json envelope as JSON. Do not create an image in this response; a separate image call follows for long-form. Give the full requested documents.',
        'max_output_tokens':24000}
    if research: payload['tools']=[{'type':'web_search'}]; payload['include']=['web_search_call.action.sources']
    data=request_json('https://api.openai.com/v1/responses',payload,token)
    if research and not any(x.get('type')=='web_search_call' for x in data.get('output',[])): raise ProviderError('Research task returned without web search. Rejected as unverified rather than accepting an unsourced assessment.')
    result=import_result(store,job,response_text(data))
    # Checkpoint text before optional image call; never lose paid work on image failure.
    store.update_job(job['id'],'running',result)
    if job['kind']=='long':
        try:
            content=[{'type':'input_text','text':get_profile(store)['thumbnail']+'\nCreate the image from this task and transcript. Return an image.\n'+prompt}]
            for id_ in job['body'].get('file_ids',[]):
                f=store.file(id_)
                if f['name'].lower().endswith(('.png','.jpg','.jpeg','.webp')):
                    mime='image/png' if f['name'].lower().endswith('.png') else ('image/webp' if f['name'].lower().endswith('.webp') else 'image/jpeg')
                    content.append({'type':'input_image','image_url':'data:'+mime+';base64,'+base64.b64encode(store.bytes(id_)).decode()})
            img=request_json('https://api.openai.com/v1/responses',{'model':prefs.get('model','gpt-6-astra'),'store':False,'input':[{'role':'user','content':content}],
                'tools':[{'type':'image_generation','model':prefs.get('image_model','gpt-image-2.5-sunburst'),'size':'1536x1024','quality':'high'}]},token)
            if img.get('status')!='completed': raise ProviderError('Image response incomplete')
            b64=next((x.get('result') for x in img.get('output',[]) if x.get('type')=='image_generation_call'),None)
            if not b64: raise ProviderError('No image was returned')
            original=base64.b64decode(b64,validate=True)
            result['file_ids'].append(store.add_file('thumbnail_original.png',original,'thumbnail',job['title'],private=any(store.file(i)['private'] for i in job['body'].get('file_ids',[]))))
            image=Image.open(io.BytesIO(original)).convert('RGB')
            # Preserve the artwork; exact 16:9 canvas instead of cropping text/faces.
            image=ImageOps.pad(image,(1280,720),color='#110d1b',method=Image.Resampling.LANCZOS)
            out=io.BytesIO(); image.save(out,format='PNG')
            result['file_ids'].append(store.add_file('thumbnail_16x9.png',out.getvalue(),'thumbnail',job['title'],private=any(store.file(i)['private'] for i in job['body'].get('file_ids',[]))))
        except Exception:
            store.update_job(job['id'],'partial',result,'Text saved. Thumbnail failed; review provider usage and use a Work packet or attach your image. Text was not regenerated.')
            return
    store.update_job(job['id'],'completed',result)

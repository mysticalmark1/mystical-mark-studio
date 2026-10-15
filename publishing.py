# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Mystical Mark Studio contributors
# Distributed WITHOUT ANY WARRANTY. See LICENSE and NOTICE.
"""Opt-in text publishing, persisted progress, no blind retries after ambiguity."""
import os, threading
from datetime import datetime, timezone, timedelta
from ai import request_json, ProviderError
from storage import LOCK, now

PUBLISH_LOCK=threading.Lock()

def connections():
    return {'X':bool(os.environ.get('X_USER_ACCESS_TOKEN')),'Threads':bool(os.environ.get('THREADS_ACCESS_TOKEN') and os.environ.get('THREADS_USER_ID'))}

def publish(store,id_):
    with PUBLISH_LOCK:
        post=store.entity(id_)
        if post['type']!='post' or post.get('state') not in ('approved','scheduled'): raise ValueError('Approve a reviewed post before publishing.')
        if not connections().get(post.get('platform')): raise ValueError('Platform credentials are not configured.')
        if not post.get('approved_at'): raise ValueError('Review approval is missing.')
        post['state']='publishing'; post['remote_ids']=post.get('remote_ids',[])
        store.entity_save('post',{k:v for k,v in post.items() if k not in ('id','type')},id_)
        try:
            for text in post['parts'][len(post['remote_ids']):]:
                previous=post['remote_ids'][-1] if post['remote_ids'] else None
                if post['platform']=='X':
                    data={'text':text}
                    if previous: data['reply']={'in_reply_to_tweet_id':previous}
                    r=request_json('https://api.x.com/2/tweets',data,os.environ['X_USER_ACCESS_TOKEN'],60)
                    remote=r.get('data',{}).get('id')
                else:
                    import urllib.parse, urllib.request, json
                    # Threads text auto-publish; token stays in Authorization, never URLs.
                    payload={'media_type':'TEXT','text':text,'auto_publish_text':'true'}
                    if previous: payload['reply_to_id']=previous
                    token=os.environ['THREADS_ACCESS_TOKEN']
                    user=os.environ['THREADS_USER_ID']
                    if not user.isdigit(): raise ValueError('THREADS_USER_ID must be numeric')
                    r=request_json('https://graph.threads.net/v1.0/'+user+'/threads',payload,token,60)
                    remote=r.get('id')
                if not remote: raise ProviderError('No remote post ID returned')
                post['remote_ids'].append(str(remote))
                store.entity_save('post',{k:v for k,v in post.items() if k not in ('id','type')},id_)
            post['state']='published'; post['published_at']=now(); post['error']=''
        except Exception:
            post['state']='uncertain'; post['error']='Publishing stopped. Some posts may be live. Check the platform and saved remote IDs before creating another attempt; automatic retry is disabled.'
        store.entity_save('post',{k:v for k,v in post.items() if k not in ('id','type')},id_)
        return post

def tick(store):
    for post in store.entities('post'):
        if post.get('state')!='scheduled': continue
        when=datetime.fromisoformat(post['scheduled_at'])
        current=datetime.now(timezone.utc)
        if current<when: continue
        if current-when>timedelta(minutes=15):
            post['state']='overdue'; post['error']='The scheduled time was missed by more than 15 minutes. Review and reschedule or publish now.'
            store.entity_save('post',{k:v for k,v in post.items() if k not in ('id','created','updated')},post['id'])
        else:
            try: publish(store,post['id'])
            except ValueError as exc:
                post['state']='blocked'; post['error']=str(exc)
                store.entity_save('post',{k:v for k,v in post.items() if k not in ('id','created','updated')},post['id'])

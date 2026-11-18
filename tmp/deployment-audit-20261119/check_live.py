import json
import time
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import httpx
import pymupdf
from docx import Document
from PIL import Image, ImageDraw, ImageFont

BASE='https://brandguard-ai-pt15.onrender.com'
OUT=Path(__file__).parent
results=[]
c=httpx.Client(base_url=BASE,timeout=60)

def req(method,path,expected=200,**kw):
    r=c.request(method,path,**kw)
    assert r.status_code==expected, f'{method} {path}: expected {expected}, got {r.status_code}: {r.text[:200]}'
    return r

def role(name):
    req('PUT','/api/demo/role',json={'role':name})

def create(content='magic AI',campaign='Live audit',**kw):
    role('creator')
    return req('POST','/api/submissions',201,json=dict(title='Deployment verification',content=content,campaign=campaign,content_type='Advertisement',platform='Web',**kw)).json()

def action(s,path,**kw):
    return req('POST',f"/api/submissions/{s['id']}/{path}",json=dict(generation=s['generation'],**kw)).json()

def latest(s): return s['versions'][-1]['reviews'][-1]

def check(name,fn):
    start=time.monotonic()
    try:
        detail=fn()
        result=dict(name=name,status='PASS',seconds=round(time.monotonic()-start,2),detail=detail)
    except Exception as exc:
        result=dict(name=name,status='FAIL',seconds=round(time.monotonic()-start,2),detail=str(exc))
    results.append(result)
    print(json.dumps(result),flush=True)

def access():
    req('GET','/api/knowledge',401)
    r=req('POST','/api/demo',201)
    cookie=r.headers.get('set-cookie','').lower()
    assert 'secure' in cookie and 'httponly' in cookie and 'samesite=strict' in cookie
    assert req('GET','/api/analytics').json()['total']==0
    assert req('GET','/api/session').json()['demo']
    return 'Fresh private workspace; unauthenticated access rejected; Secure/HttpOnly/SameSite cookie.'

def files():
    role('creator')
    text='Approved terminology for the deployment audit.'
    doc=Document();doc.add_paragraph(text);b=BytesIO();doc.save(b)
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((72,72),text); pdf_bytes=pdf.tobytes()
    for name,data in [('audit.txt',text.encode()),('audit.pdf',pdf_bytes),('audit.docx',b.getvalue())]:
        r=req('POST','/api/extract',files={'file':(name,data)})
        assert r.json()['content'].strip()==text
    for name,data,status in [('broken.pdf',b'bad',422),('unsupported.svg',b'<svg/>',415),('large.txt',b'x'*(5*1024*1024+1),413)]:
        req('POST','/api/extract',status,files={'file':(name,data)})
    req('POST','/api/artwork',422,files={'file':('broken.png',b'bad')})
    req('POST','/api/submissions',422,json=dict(title='Empty',content=' ',content_type='Ad',platform='Web'))
    return 'TXT/PDF/DOCX extracted correctly; empty copy, malformed/unsupported/oversized uploads rejected.'

def permissions_history():
    s=create();sid=s['id']
    assert latest(s)['findings'][0]['source_id']
    queued=action(s,'submit-for-approval')
    req('POST',f'/api/submissions/{sid}/decision',403,json=dict(generation=queued['generation'],action='APPROVED',comment='Invalid creator decision'))
    role('reviewer');changed=action(queued,'decision',action='CHANGES_REQUESTED',comment='Use approved terminology.')
    role('creator')
    req('POST',f'/api/submissions/{sid}/reanalyze',409,json=dict(generation=s['generation'],content='Edited'))
    revised=action(changed,'reanalyze',content='Explore our AI-powered solution.')
    assert revised['revision']==2 and not latest(revised)['findings']
    queued=action(revised,'submit-for-approval')
    role('reviewer');approved=action(queued,'decision',action='APPROVED',comment='Deployment audit approved.')
    assert req('GET',f'/api/submissions/{sid}').json()['actions'][-1]['comment']=='Deployment audit approved.'
    role('creator');changed=action(approved,'reanalyze',content='Explore tools for growing teams.')
    assert changed['status']=='REVIEWED' and changed['actions'][-1]['action']=='SUPERSEDED'
    assert changed['versions'][0]['content']=='magic AI'
    role('reviewer');req('POST','/api/submissions',403,json=dict(title='Restricted',content='Hello',content_type='Ad',platform='Web'))
    with httpx.Client(base_url=BASE,timeout=30) as other:
        assert other.post('/api/demo').status_code==201
        assert other.get(f'/api/submissions/{sid}').status_code==404
        assert other.get('/api/analytics').json()['total']==0
    role('creator')
    return 'Role enforcement, stale updates, changes requested, approval, new-revision invalidation and cross-workspace isolation passed.'

def visual():
    role('admin')
    mark=Image.new('RGB',(100,70),'white');pen=ImageDraw.Draw(mark)
    pen.polygon([(7,8),(65,8),(85,33),(38,62),(7,48)],fill='#3DE0C2')
    pen.line([(17,43),(31,23),(44,48),(64,19)],fill='#132349',width=5)
    buf=BytesIO();mark.save(buf,format='PNG')
    req('POST','/api/logos',201,files={'file':('audit-logo.png',buf.getvalue())})
    art=Image.new('RGB',(900,330),'white');art.paste(mark,(35,35));pen=ImageDraw.Draw(art)
    pen.rectangle([700,0,899,329],fill='#ee1833')
    pen.text((25,210),'guaranteed results',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',48),fill='#101010')
    timings={}
    for fmt,ext in [('PNG','png'),('JPEG','jpg')]:
        buf=BytesIO();art.save(buf,format=fmt)
        role('creator');t=time.monotonic()
        image=req('POST','/api/artwork',201,files={'file':('audit.'+ext,buf.getvalue())}).json()
        s=create(content='100% accurate',artwork_id=image['id']);items=latest(s)['findings']
        timings[fmt]=round(time.monotonic()-t,2)
        assert any(f['origin']=='copy' and f['original_text']=='100% accurate' for f in items)
        assert any(f['origin']=='artwork' and 'guaranteed results' in f['original_text'].lower() and f['regions'] for f in items)
        assert any(f['category']=='Brand colours' and f['regions'] for f in items)
        assert any(f['category']=='Brand logo' and f['evidence_status']=='SUPPORTED' and f['regions'] for f in items)
    return dict(result='Real OCR, copy/artwork combined, logo match and colour regions passed for PNG and JPG.',upload_and_review_seconds=timings)

def governance():
    role('admin');source=req('GET','/api/knowledge').json()['sources'][0]['id']
    spec=dict(title='Live campaign required term',description='Use the approved term.',kind='required',category='Terminology',severity='medium',pattern='magic AI',source_id=source)
    rule=req('POST','/api/rules',201,json=spec).json()
    a=create(campaign='Governance audit');a=action(a,'reanalyze',content='magic AI')
    b=create(campaign='Governance audit');create(campaign='Separate audit campaign')
    role('admin');req('PUT','/api/rules/'+rule['id'],json={**spec,'pattern':'Approved phrase'})
    clean=create(content='Approved phrase',campaign='Governance audit')
    rows=req('GET','/api/governance',params={'campaign':'Governance audit'}).json()
    old,new=sorted([r for r in rows if r['rule_id']==rule['id']],key=lambda r:r['version'])
    assert (old['flagged'],old['assessed'],old['conflicts'])==(2,2,2)
    assert (new['flagged'],new['assessed'],new['conflicts'])==(0,1,0)
    evidence=req('GET','/api/governance/evidence',params={'campaign':'Governance audit','rule_id':rule['id'],'version':1,'flag':'conflict'}).json()
    assert {r['review_id'] for r in evidence['reviews']}=={latest(a)['id'],latest(b)['id']}
    return 'Two conflicting revisions counted once each; other campaign excluded; v2 clean assessment and exact evidence IDs verified.'

def wordpress():
    role('admin')
    archive=req('GET','/api/integrations/wordpress/plugin.zip')
    assert set(ZipFile(BytesIO(archive.content)).namelist())=={'brandguard/brandguard.php','brandguard/editor.js'}
    key=req('POST','/api/integrations/wordpress').json()['key']
    headers={'Authorization':'Bearer '+key}
    snapshot=dict(title='Deployment audit',content='<p>magic AI</p>',excerpt='Audit excerpt',slug='deployment-audit',featured_media=12)
    path='/api/wordpress/posts/938271'
    def digest(s):
        h=sha256()
        for field in ['title','content','excerpt','slug','featured_media']:
            raw=str(s[field]).encode();h.update(str(len(raw)).encode()+b':'+raw)
        return h.hexdigest()
    try:
        sent=req('POST',path,headers=headers,json={'snapshot':snapshot}).json()
        again=req('POST',path,headers=headers,json={'snapshot':snapshot}).json()
        assert sent==again and sent['status']=='PENDING_APPROVAL'
        role('reviewer');s=req('GET','/api/submissions/'+sent['submission_id']).json()
        action(s,'decision',action='APPROVED',comment='Live API audit approval.')
        assert req('GET',path,headers=headers,params={'digest':digest(snapshot)}).json()['status']=='APPROVED'
        for field,value in [('title','Changed title'),('content','<p><strong>magic AI</strong></p>'),('excerpt','Changed'),('slug','changed'),('featured_media',13)]:
            assert req('GET',path,headers=headers,params={'digest':digest({**snapshot,field:value})}).json()['status']=='NEEDS_REVIEW'
    finally:
        role('admin');req('DELETE','/api/integrations/wordpress',204)
    req('GET',path,401,headers=headers,params={'digest':digest(snapshot)})
    return 'Plugin ZIP, snapshot submission, idempotency, approval, five changed fields and revocation passed. Real WordPress editor not exercised.'

try:
    for name,fn in [('Access and session cookies',access),('Document imports and invalid inputs',files),('Permissions, revisions and isolation',permissions_history),('PNG and JPG visual review',visual),('Campaign governance',governance),('WordPress integration API',wordpress)]:
        check(name,fn)
finally:
    c.close()
    (OUT/'api-results.json').write_text(json.dumps(dict(url=BASE,date='2026-11-19',results=results),indent=2),encoding='utf-8')

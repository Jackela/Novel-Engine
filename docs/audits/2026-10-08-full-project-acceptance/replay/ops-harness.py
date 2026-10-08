import json, os, pathlib, subprocess, sys, time, urllib.request, urllib.error, hashlib, uuid, zipfile, socket, xml.etree.ElementTree as ET

ROOT=pathlib.Path(os.environ.get('NOVEL_ENGINE_REPLAY_ROOT',os.getcwd()))
BASE=pathlib.Path(os.environ['NOVEL_ENGINE_REPLAY_EVIDENCE'])
STATE=BASE/'ops-state.json'
RELEASE='ghcr.io/jackela/novel-engine@sha256:15df0fa2b7aca06b30fd412c5dce46a353f57d1de905a7aac1db29440f742c93'
SOURCE=os.environ.get('NOVEL_ENGINE_REPLAY_IMAGE','novel-engine-acp-audit:final')
ENV={key:os.environ[key] for key in ('PATH','HOME','DOCKER_HOST','DOCKER_CONTEXT') if key in os.environ}
state=json.loads(STATE.read_text()) if STATE.exists() else {'checks':[],'profiles':{}}
LOG=BASE/('ops-'+sys.argv[1]+'.log')

def save(): STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2))
def log(value):
    with LOG.open('a') as stream: stream.write(value+'\n')
    print(value,flush=True)
def run(args,check=True,timeout=120):
    log('$ '+ ' '.join(args))
    result=subprocess.run(args,capture_output=True,text=True,env=ENV,timeout=timeout)
    log(result.stdout+result.stderr)
    if check and result.returncode: raise RuntimeError('command failed '+str(result.returncode)+': '+' '.join(args))
    return result
def record(name,body,source):
    check={'name':name,'source':source,'log':str(LOG),'at':time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    try: check['details']=body(); check['status']='pass'
    except Exception as error: check.update(status='fail',error=str(error)); log('CHECK FAILED '+name+': '+str(error))
    state['checks'].append(check); save(); return check
def profile(kind,image):
    project='ne-ops-'+kind+'-'+uuid.uuid4().hex[:8]
    directory=BASE/('ops-'+project); directory.mkdir()
    override=directory/'ops-compose.override.yaml'
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1',0)); port=reserve.getsockname()[1]
    override.write_text('services:\n  novel-engine:\n    image: '+image+'\n    ports: !override\n      - "127.0.0.1:'+str(port)+':8000"\n    environment:\n      SECURITY_CORS_ORIGINS: https://ops.example.invalid\n      LLM_PROVIDER: mock\n      LOG_LEVEL: warn\n')
    result={'project':project,'directory':str(directory),'override':str(override),'image':image}
    state['profiles'][kind]=result; save(); return result
def compose(p,*args,check=True):
    return run(['docker','compose','--project-name',p['project'],'--project-directory',p['directory'],'--env-file','/dev/null','-f',str(ROOT/'compose.yaml'),'-f',p['override'],*args],check=check)
def start(p):
    compose(p,'up','-d','--no-build','--pull','never')
    p['container']=compose(p,'ps','-q','novel-engine').stdout.strip()
    info=json.loads(run(['docker','inspect',p['container']]).stdout)[0]
    host=info['HostConfig']; config=info['Config']
    p['port']=int(info['NetworkSettings']['Ports']['8000/tcp'][0]['HostPort'])
    p['base']='http://127.0.0.1:'+str(p['port'])
    p['volume']=next(m['Name'] for m in info['Mounts'] if m['Destination']=='/app/data')
    p['image_id']=info['Image']
    p['hardening']={key:host.get(key) for key in ['ReadonlyRootfs','CapDrop','SecurityOpt','Memory','NanoCpus','PidsLimit','Tmpfs']}
    p['user']=config.get('User')
    save()
def ready(p,seconds=45):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        try:
            with urllib.request.urlopen(p['base']+'/health/ready',timeout=2) as response:
                if response.status==200: return json.loads(response.read())
        except (urllib.error.URLError,TimeoutError,ConnectionError): pass
        time.sleep(1)
    compose(p,'logs','--no-color','--tail','40',check=False)
    raise RuntimeError('readiness did not become healthy in '+str(seconds)+'s')
def api(p,method,path,payload=None,auth=True,binary=False):
    headers={'Origin':'https://ops.example.invalid'}
    if payload is not None: headers['Content-Type']='application/json'
    if auth and p.get('cookies'):
        headers['Cookie']=p['cookies']; headers['x-csrf-token']=p['csrf']
    request=urllib.request.Request(p['base']+path,data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None,headers=headers,method=method)
    try:
        response=urllib.request.urlopen(request,timeout=30); data=response.read()
        if path=='/api/session/login':
            cookies=[x.split(';',1)[0] for x in response.headers.get_all('Set-Cookie',[])]
            p['cookies']='; '.join(cookies)
            p['csrf']=next(x.split('=',1)[1] for x in cookies if x.startswith('novel_engine_csrf='))
        log(method+' '+path+' -> '+str(response.status))
        return data if binary else json.loads(data)
    except urllib.error.HTTPError as error:
        raise RuntimeError(method+' '+path+' -> '+str(error.code)+' '+error.read().decode())
def initialize(p):
    token_result=run(['docker','exec',p['container'],'cat','/app/data/.setup-token'],check=False)
    p['setup_token_present']=token_result.returncode==0
    headers={'Content-Type':'application/json','Origin':'https://ops.example.invalid'}
    if p['setup_token_present']: headers['x-setup-token']=token_result.stdout.strip()
    elif p['image']!=RELEASE: raise RuntimeError('candidate missing setup token')
    request=urllib.request.Request(p['base']+'/api/setup',data=json.dumps({'username':'ops-owner','password':'ops-synthetic-password-20261008'}).encode(),headers=headers,method='POST')
    with urllib.request.urlopen(request) as response: assert response.status==201
    api(p,'POST','/api/session/login',{'username':'ops-owner','password':'ops-synthetic-password-20261008'},auth=False)
    project=api(p,'POST','/api/projects',{'title':'运维验收合成书稿'})
    document=api(p,'POST','/api/projects/'+project['id']+'/documents',{'kind':'chapter','title':'第一章 验收','content_markdown':'# 第一章 验收\n\n合成验收正文 A：中文标点，英文 Alpha 123。\n\n第二段，包含 **加粗** 与 *强调*。'})
    p.update(project_id=project['id'],document_id=document['id'],revision=document['current_revision_id'],content=document['content_markdown'])
    # Runtime session credentials remain only in the private temporary state.
    save(); return {'project_id':p['project_id'],'document_id':p['document_id'],'version':api(p,'GET','/version',auth=False)}
def document(p): return api(p,'GET','/api/projects/'+p['project_id']+'/documents/'+p['document_id'])
def persistence(p,signal=None):
    if signal: run(['docker','exec',p['container'],'node','-e',"process.kill(1,'SIGKILL')"],check=False)
    else: compose(p,'restart','novel-engine')
    time.sleep(2); ready(p)
    current=document(p); assert current['content_markdown']==p['content']
    assert api(p,'GET','/api/session')['kind']=='owner'
    return {'content_unchanged':True,'session_retained':True,'revision':current['current_revision_id']}
def integrity(p):
    code="const D=require('/app/server/node_modules/better-sqlite3');const d=new D('/app/data/novel-engine.sqlite3',{readonly:true});console.log(JSON.stringify({check:d.pragma('quick_check',{simple:true}),migrations:d.prepare('select count(*) n from __drizzle_migrations').get().n,uid:process.getuid()}));d.close();"
    value=json.loads(run(['docker','exec',p['container'],'node','-e',code]).stdout); assert value['check']=='ok'; return value
def exports(p):
    for format in ('markdown','docx','epub'):
        job=api(p,'POST','/api/projects/'+p['project_id']+'/exports',{'format':format}); assert job['status']=='completed',job
    catalog=api(p,'GET','/api/projects/'+p['project_id']+'/exports')['exports']
    results=[]
    for artifact in catalog:
        data=api(p,'GET',artifact['download_url'],binary=True); checksum=hashlib.sha256(data).hexdigest()
        assert checksum==artifact['checksum_sha256']; assert len(data)==artifact['size_bytes']
        extension={'markdown':'md','docx':'docx','epub':'epub'}[artifact['format']]
        path=BASE/('ops-'+artifact['format']+'.'+extension); path.write_bytes(data)
        item={'format':artifact['format'],'path':str(path),'sha256':checksum,'bytes':len(data),'snapshot_id':artifact['snapshot_id']}
        if artifact['format']=='markdown':
            text=data.decode(); assert '合成验收正文 A' in text; assert text.count('第一章 验收')==1; item['content_present']=True
        else:
            with zipfile.ZipFile(path) as archive:
                assert archive.testzip() is None
                if artifact['format']=='docx':
                    xml=ET.fromstring(archive.read('word/document.xml')); ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    text=''.join(xml.itertext()); assert '合成验收正文 A' in text
                    assert 'SimSun' in archive.read('word/document.xml').decode()
                    item.update(content_present=True,xml_well_formed=True,east_asia_font=True)
                else:
                    assert archive.infolist()[0].filename=='mimetype'; assert archive.infolist()[0].compress_type==zipfile.ZIP_STORED
                    assert archive.read('mimetype')==b'application/epub+zip'
                    html=''.join(archive.read(n).decode() for n in archive.namelist() if n.endswith('.xhtml')); assert '合成验收正文 A' in html
                    opf=next(n for n in archive.namelist() if n.endswith('.opf')); ET.fromstring(archive.read(opf)); assert 'zh' in archive.read(opf).decode()
                    item.update(content_present=True,zip_and_opf_valid=True,language='zh')
        results.append(item)
    return results
def backup_restore(p):
    compose(p,'stop','novel-engine')
    backup=compose(p,'run','--rm','--no-deps','--pull','never','-T','novel-engine','node','server/dist/apps/cli/main.js','backup').stdout.strip().splitlines()[-1]
    assert backup.endswith('.sqlite3.bak'),backup
    compose(p,'start','novel-engine'); ready(p)
    current=document(p); changed=api(p,'PUT','/api/projects/'+p['project_id']+'/documents/'+p['document_id'],{'content_markdown':'合成验收正文 B：恢复测试后应消失。','base_revision_id':current['current_revision_id']})
    assert changed['content_markdown'].startswith('合成验收正文 B')
    compose(p,'stop','novel-engine')
    restored=compose(p,'run','--rm','--no-deps','--pull','never','-T','novel-engine','node','server/dist/apps/cli/main.js','restore','--input',backup)
    compose(p,'start','novel-engine'); ready(p)
    api(p,'POST','/api/session/login',{'username':'ops-owner','password':'ops-synthetic-password-20261008'},auth=False)
    current=document(p); assert current['content_markdown']==p['content']
    return {'backup':backup,'restored_original_content':True,'restore_output':restored.stdout.strip()}

if __name__ == "__main__":
    mode=sys.argv[1]
    if mode in ('release','candidate'):
        image=RELEASE if mode=='release' else SOURCE
        p=profile(mode,image)
        record(mode+'-compose-start',lambda:(start(p),ready(p),p['hardening'])[2],image)
        if p.get('container'):
            good=record(mode+'-fresh-owner-and-manuscript',lambda:initialize(p),image)
            record(mode+'-runtime-integrity',lambda:integrity(p),image)
            if good['status']=='pass':
                record(mode+'-restart-persistence',lambda:persistence(p),image)
                record(mode+'-sigkill-persistence',lambda:persistence(p,'KILL'),image)
                if mode=='candidate':
                    record('candidate-three-format-exports',lambda:exports(p),image)
                    record('candidate-cli-backup-restore',lambda:backup_restore(p),image)
                    record('candidate-post-restore-integrity',lambda:integrity(p),image)
    elif mode=='upgrade':
        p=state['profiles']['release']; compose(p,'stop','novel-engine')
        p['image']=SOURCE
        override=pathlib.Path(p['override']); override.write_text(override.read_text().replace(RELEASE,SOURCE))
        record('released-0.8-to-candidate-upgrade',lambda:(start(p),ready(p),document(p),integrity(p))[3],SOURCE)
    elif mode=='release-seed':
        p=state['profiles']['release']
        record('release-legacy-setup-and-manuscript',lambda:initialize(p),RELEASE)
        if p.get('project_id'):
            record('release-restart-persistence',lambda:persistence(p),RELEASE)
            record('release-sigkill-persistence',lambda:persistence(p,'KILL'),RELEASE)
            record('release-data-ownership',lambda:run(['docker','exec',p['container'],'stat','-c','%u:%g %a %n','/app/data','/app/data/.secret','/app/data/novel-engine.sqlite3']).stdout.strip(),RELEASE)
    elif mode=='release-replay':
        p=state['profiles']['release']
        override=pathlib.Path(p['override'])
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1',0)); port=reserve.getsockname()[1]
        override.write_text(override.read_text().replace('127.0.0.1::8000','127.0.0.1:'+str(port)+':8000'))
        start(p); ready(p)
        record('release-fixed-port-restart-persistence',lambda:persistence(p),RELEASE)
        record('release-crash-sigkill-persistence',lambda:persistence(p,'KILL'),RELEASE)
        record('release-data-ownership',lambda:run(['docker','exec',p['container'],'stat','-c','%u:%g %a %n','/app/data','/app/data/.secret','/app/data/novel-engine.sqlite3']).stdout.strip(),RELEASE)
    elif mode=='permission-probe':
        p=state['profiles']['release']
        record('release-volume-readable-and-writable-as-current-node-user',lambda:run(['docker','exec','--user','node',p['container'],'sh','-c','test -r /app/data/.secret && test -w /app/data && echo node-volume-permissions-ok']).stdout.strip(),str(ROOT/'Dockerfile')+':50')
    elif mode=='cleanup':
        for kind,p in state['profiles'].items():
            # Exact project ownership is asserted before removing only synthetic resources.
            if p.get('container'):
                label=run(['docker','inspect',p['container'],'--format','{{index .Config.Labels "com.docker.compose.project"}}'],check=False)
                if label.returncode==0 and label.stdout.strip()!=p['project']: raise RuntimeError('refuse foreign container cleanup')
            result=compose(p,'down','--volumes','--remove-orphans',check=False)
            p['cleanup']={'status':'pass' if result.returncode==0 else 'fail','at':time.strftime('%Y-%m-%dT%H:%M:%S%z')}; save()
    else: raise RuntimeError('unknown mode')

import importlib.util, pathlib, json, os, subprocess, time, threading, urllib.request, uuid, shutil
spec=importlib.util.spec_from_file_location('ops_common',str(pathlib.Path(__file__).with_name('ops-harness.py')))
ops=importlib.util.module_from_spec(spec); spec.loader.exec_module(ops)
base=ops.BASE.resolve(); p=ops.state['profiles']['candidate']
materials=base/'ops-acp-materials'; materials.mkdir(exist_ok=True); materials.chmod(0o755)
(materials/'source-copy.md').write_text((ops.BASE/'ops-markdown.md').read_text())
token_file=base/'ops-host-token'; ready_file=base/'ops-host-ready.json'
gateway_log=(base/'ops-host-gateway.log').open('w')
ready_file.unlink(missing_ok=True)
gateway=subprocess.Popen([shutil.which('node'),str(pathlib.Path(__file__).with_name('ops-host-gateway.mjs')),str(token_file),str(ready_file)],stdout=gateway_log,stderr=gateway_log,env=ops.ENV)
secret_volume=p['project']+'_acp-secret'
try:
    for _ in range(100):
        if ready_file.exists(): break
        if gateway.poll() is not None: raise RuntimeError('temporary gateway exited')
        time.sleep(.05)
    address=json.loads(ready_file.read_text()); port=address['port']
    ops.state['temporary_gateway']={'pid':gateway.pid,'host':'0.0.0.0','port':port,'token_file':str(token_file),'status':'running'};ops.save()
    dns_probe="for(const host of ['host.lima.internal','host.docker.internal','192.168.5.2']){try{const r=await fetch('http://'+host+':"+str(port)+"/acp',{signal:AbortSignal.timeout(3000)});console.log(JSON.stringify({host,status:r.status}))}catch(e){console.log(JSON.stringify({host,error:e.message}))}}"
    reachable=ops.run(['docker','exec',p['container'],'node','--input-type=module','-e',dns_probe])
    assert '"host":"192.168.5.2","status":404' in reachable.stdout
    ops.run(['docker','volume','create','--label','novel-engine.audit='+p['project'],secret_volume])
    ops.state['temporary_secret_volume']=secret_volume;ops.save()
    seed_command=['docker','run','--rm','-i','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user','node','-v',secret_volume+':/app/data','--entrypoint','node',p['image_id'],'-e',"const fs=require('fs');fs.writeFileSync('/app/data/gateway.token',fs.readFileSync(0,'utf8'),{mode:0o600});console.log(JSON.stringify({uid:process.getuid(),mode:fs.statSync('/app/data/gateway.token').mode&511}));"]
    ops.log('$ '+' '.join(seed_command)+' [synthetic token supplied on stdin; not logged]')
    seeded=subprocess.run(seed_command,input=token_file.read_text(),capture_output=True,text=True,env=ops.ENV,timeout=30)
    ops.log(seeded.stdout+seeded.stderr);assert seeded.returncode==0
    override=pathlib.Path(p['override'])
    original=override.read_text().split('      ACP_PROXY_URL:',1)[0].replace(ops.SOURCE,p['image_id'])
    extra='      ACP_PROXY_URL: ws://192.168.5.2:'+str(port)+'/acp\n      ACP_PROXY_TOKEN_FILE: /run/ops-acp-secret/gateway.token\n      ACP_AGENT_COMMAND: '+shutil.which('node')+'\n      ACP_AGENT_ARGS: '+json.dumps(json.dumps([str(pathlib.Path(__file__).with_name('ops-acp-agent.mjs'))]))+'\n      ACP_WORKSPACE_ROOT: '+str(materials)+'\n'
    override.write_text(original+extra+'    volumes:\n      - type: bind\n        source: '+str(materials)+'\n        target: '+str(materials)+'\n        read_only: false\n      - type: volume\n        source: ops-acp-secret\n        target: /run/ops-acp-secret\n        read_only: true\nvolumes:\n  ops-acp-secret:\n    external: true\n    name: '+secret_volume+'\n')
    ops.start(p);ops.ready(p)
    catalog=ops.api(p,'GET','/api/providers')
    acp=next(item for item in catalog['providers'] if item['provider']=='acp'); assert acp['configured'] is True
    before=ops.document(p)
    operation=str(uuid.uuid4());events=[];ready=threading.Event();errors=[]
    scope='/api/projects/'+p['project_id']+'/ai-operations/'+operation
    def observe():
        try:
            request=urllib.request.Request(p['base']+scope+'/events',headers={'Cookie':p['cookies'],'Origin':'https://ops.example.invalid'})
            with urllib.request.urlopen(request,timeout=35) as response:
                for raw in response:
                    line=raw.decode().strip()
                    if not line.startswith('data: '):continue
                    event=json.loads(line[6:]);events.append(event)
                    if event['type']=='ready':ready.set()
                    elif event['type']=='permission':
                        selected=urllib.request.Request(p['base']+scope+'/permissions/'+event['permission_id'],data=b'{"option_id":"allow_once"}',headers={'Cookie':p['cookies'],'x-csrf-token':p['csrf'],'Origin':'https://ops.example.invalid','Content-Type':'application/json'},method='POST')
                        with urllib.request.urlopen(selected,timeout=10) as accepted:assert accepted.status==204
        except Exception as error:errors.append(str(error));ready.set()
    thread=threading.Thread(target=observe,daemon=True);thread.start();assert ready.wait(10);assert not errors,errors
    request=urllib.request.Request(p['base']+'/api/projects/'+p['project_id']+'/documents/'+p['document_id']+'/ai-proposals',data=json.dumps({'provider':'acp','operation':'rewrite','instruction':'验证宿主材料工作副本；形成提议，不接受正文。'}).encode(),headers={'Cookie':p['cookies'],'x-csrf-token':p['csrf'],'Origin':'https://ops.example.invalid','Content-Type':'application/json','x-ai-operation-id':operation},method='POST')
    with urllib.request.urlopen(request,timeout=35) as response:job=json.loads(response.read())
    thread.join(timeout=5);assert not errors,errors
    assert job['status']=='completed',job
    after=ops.document(p);assert after['content_markdown']==before['content_markdown'];assert after['current_revision_id']==before['current_revision_id']
    notes=(materials/'notes.md').read_text();assert 'Synthetic container-to-host ACP material write completed.' in notes
    assert any(e['type']=='permission' for e in events)
    assert any(e['type']=='tool' and e['status']=='completed' for e in events)
    result={'status':'pass','image_id':p['image_id'],'gateway_url':'ws://192.168.5.2:'+str(port)+'/acp','provider_catalog':acp,'job_id':job['id'],'job_status':job['status'],'model':job['model'],'host_material_write':True,'material_path':str(materials/'notes.md'),'database_content_unchanged':True,'revision_unchanged':True,'hardening':p['hardening'],'events':events,'token_mount':'separate node-owned mode0600 synthetic token volume mounted read-only','credentials':'no Grok credentials accessed or copied','log':str(ops.LOG)}
    (ops.BASE/'ops-container-acp-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));ops.log(json.dumps(result,ensure_ascii=False));ops.state['checks'].append({'name':'candidate-container-to-host-acp','status':'pass','details':result,'source':p['image_id'],'log':str(ops.LOG)});ops.save()
except Exception as error:
    result={'status':'fail','error':str(error),'log':str(ops.LOG)};(ops.BASE/'ops-container-acp-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));ops.log(json.dumps(result));ops.state['checks'].append({'name':'candidate-container-to-host-acp','status':'fail','details':result,'source':p['image_id'],'log':str(ops.LOG)});ops.save()
finally:
    gateway.terminate()
    try:gateway.wait(timeout=10)
    except subprocess.TimeoutExpired:gateway.kill();gateway.wait()
    gateway_log.close();ops.state['temporary_gateway']['status']='stopped';ops.save()

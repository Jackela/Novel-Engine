import {execFileSync as replayGit} from 'node:child_process';
import { pathToFileURL as replayFileUrl } from 'node:url';
const replayRoot=process.env.NOVEL_ENGINE_REPLAY_ROOT ?? process.cwd();
const replayCandidateSha=replayGit('git',['-C',replayRoot,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const replayEvidence=process.env.NOVEL_ENGINE_REPLAY_EVIDENCE;
if(!replayEvidence)throw Error('Set NOVEL_ENGINE_REPLAY_EVIDENCE to a fresh isolated directory.');
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';
import assert from 'node:assert/strict';
const { buildApp }=await import(replayFileUrl(replayRoot+"/server/dist/apps/api/app.js").href);
const { loadServerConfig }=await import(replayFileUrl(replayRoot+"/server/dist/shared/infrastructure/config/server_config.js").href);
const { AcpGateway }=await import(replayFileUrl(replayRoot+"/server/dist/shared/interface/acp/AcpGateway.js").href);
const { AcpAgentProcess }=await import(replayFileUrl(replayRoot+"/server/dist/shared/infrastructure/acp/AcpAgentProcess.js").href);
const dir=replayEvidence;
const materials=join(dir,'frozen-grok-materials'),data=join(dir,'frozen-grok-data');
await mkdir(materials,{recursive:true});await mkdir(data,{recursive:true});
await mkdir(join(materials,'.grok'),{recursive:true});
await writeFile(join(materials,'.grok/sandbox.toml'),`[profiles.novel-engine]\nextends = "strict"\ndeny = [${JSON.stringify(data)}, "**/*.sqlite3", "**/.env", "**/.env.*", "**/*.db", "**/*.pem", "**/*.key"]\n`);
await writeFile(join(data,'authority-canary.txt'),'SYNTHETIC_AUTHORITY_CANARY');
await writeFile(join(materials,'materials.md'),'Mira keeps a red notebook at the harbor. 林舟在港口保管一本红色笔记本。\n');
const tokenFile=join(dir,'frozen-grok-proxy-token');const token=randomUUID();await writeFile(tokenFile,token,{mode:0o600});
const diagnostic=[];const gateway=new AcpGateway({token,launchAgent:AcpAgentProcess.launch,diagnostic:line=>diagnostic.push(line)});
const {url}=await gateway.listen({port:0});
const config=loadServerConfig({envFile:null,env:{APP_ENVIRONMENT:'testing',DB_URL:`sqlite:///${join(data,'novel-engine.sqlite3')}`,SECURITY_SECRET_KEY:'synthetic-grok-studio-secret-1234567890',SECURITY_CORS_ORIGINS:'http://127.0.0.1:4382',SECURITY_RATE_LIMIT:'10000/minute',ACP_PROXY_URL:url,ACP_PROXY_TOKEN_FILE:tokenFile,ACP_AGENT_COMMAND:(process.env.NOVEL_ENGINE_REPLAY_GROK ?? '/Users/jackela/.grok/bin/grok'),ACP_WORKSPACE_ROOT:materials}});
const app=await buildApp({logger:false,config});const address=await app.listen({host:'127.0.0.1',port:0});
const password='synthetic-grok-owner-password-123';
await app.inject({method:'POST',url:'/api/setup',payload:{username:'owner',password}});
const login=await app.inject({method:'POST',url:'/api/session/login',payload:{username:'owner',password}});assert.equal(login.statusCode,200);
const pairs=login.headers['set-cookie'].map(x=>x.split(';')[0]);const cookie=pairs.join('; ');const csrf=pairs.find(x=>x.startsWith('novel_engine_csrf=')).split('=')[1];
const headers={cookie,'x-csrf-token':csrf};
async function call(method,url,payload,extra={}){const r=await app.inject({method,url,headers:{...headers,...extra},...(payload===undefined?{}:{payload})});if(r.statusCode>=400)throw new Error(`${method} ${url}: ${r.statusCode} ${r.body}`);return r.json();}
const results=[];
async function observed(projectId,path,payload,decision='allow',whilePending=async()=>{}) {
  const operationId=randomUUID(),controller=new AbortController(),events=[];
  const stream=await fetch(`${address}/api/projects/${projectId}/ai-operations/${operationId}/events`,{headers,signal:controller.signal});
  const reader=stream.body.getReader();let buffer='';const decoder=new TextDecoder();let readyResolve;const ready=new Promise(r=>readyResolve=r);
  const consume=(async()=>{try {for(;;){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let end;while((end=buffer.indexOf('\n\n'))>=0){const frame=buffer.slice(0,end);buffer=buffer.slice(end+2);const line=frame.split('\n').find(x=>x.startsWith('data: '));if(!line)continue;const event=JSON.parse(line.slice(6));events.push(event);if(event.type==='ready')readyResolve();if(event.type==='permission'){const option=event.options.find(x=>x.kind.startsWith(decision==='allow'?'allow':'reject'));if(!option)throw Error('Missing expected permission option');await call('POST',`/api/projects/${projectId}/ai-operations/${operationId}/permissions/${event.permission_id}`,{option_id:option.option_id});}}}}catch(error){if(!controller.signal.aborted)throw error;}})();
  await ready;const started=Date.now();const pending=call('POST',path,payload,{'x-ai-operation-id':operationId});await new Promise(r=>setTimeout(r,700));await whilePending();const job=await pending;await consume;
  return {job,events,elapsed_ms:Date.now()-started};
}

const {createRequire}=await import('node:module');const require=createRequire(replayRoot+'/server/package.json');const Database=require('better-sqlite3');
const persist=async()=>writeFile(join(dir,'frozen-grok-results.json'),JSON.stringify({candidate_sha:replayCandidateSha,grok_cli:'1.0.46',results},null,2));
try {
 const p=await call('POST','/api/projects',{title:'Final candidate captured review'});await call('PATCH',`/api/projects/${p.id}`,{settings:{provider:'acp'}});
 const seed=p.documents.find(d=>d.kind==='chapter');const path=`/api/projects/${p.id}/documents/${seed.id}`;const initial=await call('GET',path);
 const padding='清晨，林舟坐在内陆小镇的书房里整理笔记。窗外的街道安静，邻居们刚刚开门。她把这一周的生活逐日记在纸上，日期和顺序都很清楚。'.repeat(10);
 const contradiction='林舟从出生到今天从未到过海边，这是明确事实，并非失忆、梦境、谎言或多重时间线。\n\n同一天，林舟在日记中准确写道，她过去连续十年每天都在海边同一座灯塔值班，这是明确事实，并非幻想、传闻或隐喻。\n\n'+padding;
 const captured=await call('PUT',path,{base_revision_id:initial.current_revision_id,content_markdown:contradiction,autosave:true});
 let newest;
 const review=await observed(p.id,`/api/projects/${p.id}/reviews`,{},'allow',async()=>{
  const second=await call('PUT',path,{base_revision_id:captured.current_revision_id,content_markdown:'作者在等待评审时第一次修改正文。'+padding,autosave:true});
  newest=await call('PUT',path,{base_revision_id:second.current_revision_id,content_markdown:'作者在等待评审时第二次修改正文。'+padding,autosave:true});
 });
 assert.equal(review.job.status,'completed',review.job.error);const detail=await call('GET',`/api/projects/${p.id}/reviews/${review.job.result.review_id}`);
 const db=new Database(join(data,'novel-engine.sqlite3'),{readonly:true});
 const pinned=db.prepare('SELECT revision_id FROM snapshot_documents WHERE snapshot_id=? AND document_id=?').get(detail.snapshot_id,seed.id);
 assert.equal(pinned.revision_id,captured.current_revision_id);assert.equal((await call('GET',path)).current_revision_id,newest.current_revision_id);
 results.push({step:'editorial_review_concurrent_autosave',status:'pass',job:review.job,detail,events:review.events,captured_revision:captured.current_revision_id,newest_revision:newest.current_revision_id,snapshot_revision:pinned.revision_id,elapsed_ms:review.elapsed_ms});await persist();console.log('captured review',review.job.status,review.job.model,'original snapshot retained');
 const correct='林舟出生于内陆，直到十年前才第一次来到海边。此后她连续十年在同一座灯塔值班。今天她如实写下第一次看见大海时的惊喜和十年工作的经历，事情的时间顺序清楚，并无失忆、梦境或隐喻。\n\n'+padding;
 const controlSaved=await call('PUT',path,{base_revision_id:newest.current_revision_id,content_markdown:correct});
 const control=await observed(p.id,`/api/projects/${p.id}/reviews`,{});assert.equal(control.job.status,'completed',control.job.error);const controlDetail=await call('GET',`/api/projects/${p.id}/reviews/${control.job.result.review_id}`);
 results.push({step:'editorial_review_correct_control',status:'pass',job:control.job,detail:controlDetail,events:control.events,source_revision:controlSaved.current_revision_id,elapsed_ms:control.elapsed_ms});await persist();console.log('control review',control.job.status,control.job.model,controlDetail.issues.length);
 for(const operation of ['continue','rewrite']) {
  const out=await observed(p.id,`${path}/ai-proposals`,{provider:'acp',operation,instruction:'用中文写至少600字小说正文。先读取materials.md，然后在当前工作目录的draft-notes.md追加一条简短记录。正文只在JSON规定字段返回。'});
  assert.equal(out.job.status,'completed',out.job.error);assert.equal((await call('GET',path)).current_revision_id,controlSaved.current_revision_id);
  results.push({step:operation==='continue'?'chapter_draft':'chapter_revision',status:'pass',...out,formal_revision_unchanged:true});await persist();console.log(operation,out.job.status,out.job.model);
 }
 const lore=await observed(p.id,`/api/projects/${p.id}/lore-extractions`,{provider:'acp',segment:correct});assert.equal(lore.job.status,'completed',lore.job.error);
 results.push({step:'lore_extract',status:'pass',...lore});await persist();console.log('lore',lore.job.status,lore.job.model);
 const usage=db.prepare('SELECT * FROM usage_events').all();const jobs=db.prepare('SELECT id, kind, status, model FROM jobs').all();
 await writeFile(join(dir,'frozen-grok-ledger.json'),JSON.stringify({candidate_sha:replayCandidateSha,jobs,usage,job_count:jobs.length,usage_count:usage.length,review_usage_missing:jobs.filter(x=>x.kind==='review').length,source:'actual synthetic SQLite, read-only after operations'},null,2));db.close();
 await writeFile(join(dir,'frozen-grok-summary.json'),JSON.stringify({candidate_sha:replayCandidateSha,checks:results.map(({step,status,job,detail,elapsed_ms})=>({step,status,model:job.model,job_status:job.status,issue_count:detail?.issues.length,issues:detail?.issues.map(x=>({code:x.code,message:x.message,dimension:x.evidence?.dimension})),elapsed_ms})),notes:await readFile(join(materials,'draft-notes.md'),'utf8'),native_permission_requests:results.flatMap(x=>x.events??[]).filter(x=>x.type==='permission').length},null,2));
} finally {await app.close();await gateway.close();}

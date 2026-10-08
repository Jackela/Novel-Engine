import json,hashlib,subprocess
from pathlib import Path
R=Path(__import__('os').environ.get('NOVEL_ENGINE_REPLAY_ROOT', __import__('os').getcwd()));D=R/'docs/audits/2026-10-08-full-project-acceptance';CODE='da025b7de90a6b2106892d5d8490bbdfd8628a20';valid={'pass','fail','not run','blocked','not applicable'}
x=json.loads((D/'spec-coverage.json').read_text());h=json.loads((D/'historical-remediation.json').read_text());ids=set();refs=set();direct=0
for key,n,m in [('requirements',105,513),('baseline_active_delta',1,7),('new_candidate_delta',8,32)]:
 rows=x[key];assert len(rows)==n and sum(len(r['scenarios']) for r in rows)==m
 for r in rows:
  assert r['status'] in valid and r['closure_conditions'];assert r['scenario_count']==len(r['scenarios']);assert r['id'] not in ids;ids.add(r['id']);text=(R/r['source']['path']).read_text();assert text.splitlines()[r['source']['line']-1]=='### Requirement: '+r['title'];assert r['requirement_body'] in text
  for s in r['scenarios']:
   assert s['status'] in valid and s['closure_conditions'];assert s['id'] not in ids;ids.add(s['id']);assert s['body'] in text;assert text.splitlines()[s['source_line']-1]=='#### Scenario: '+s['title']
   if s['status']=='pass':assert s['direct_case_mapping'] or s.get('direct_observation_mapping')
   for c in s['direct_case_mapping']:assert c['test_title'] in (R/c['path']).read_text().splitlines()[c['line']-1];direct+=1
  for ref in r['implementation']+r['tests']:
   raw=(R/ref['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];assert subprocess.check_output(['git','show',CODE+':'+ref['path']],cwd=R)==raw;refs.add(ref['path'])
assert len(h['items'])==54 and {i['id'] for i in h['items']}=={f'DR-{j:03}' for j in range(1,49)}|{f'DEC-{j:02}' for j in range(1,7)}
for i in h['items']:assert i['status'] in valid and i['closure_conditions'];assert i['historical_record'] in (R/i['source']['path']).read_text()
for name in ('findings','evidence-registry'):
 data=json.loads((D/(name+'.json')).read_text());rows=data.get('findings',data.get('checks'));assert all(r['status'] in valid for r in rows)
print(json.dumps({'status':'pass','source_sha':CODE,'counts':'105/513 +EOF1/7 +ACP8/32 +48DR/6DEC','source_references':len(refs),'direct_case_mappings':direct,'spec_statistics':x['status_statistics'],'history_statistics':h['status_statistics']},ensure_ascii=False))

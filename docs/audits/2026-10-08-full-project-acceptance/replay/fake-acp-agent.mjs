import { createInterface } from 'node:readline';
import { appendFile } from 'node:fs/promises';
import { join } from 'node:path';
const pending = new Map();
const send = (message) => process.stdout.write(JSON.stringify({jsonrpc:'2.0', ...message})+'\n');
const update = (update) => send({method:'session/update',params:{sessionId:'fake-session',update}});
for await (const line of createInterface({input:process.stdin})) {
  const m = JSON.parse(line);
  const reply = (result) => send({id:m.id,result});
  if (m.method === 'initialize') reply({protocolVersion:1,agentCapabilities:{},authMethods:[{id:'cached_token',name:'Cached'}]});
  else if (m.method === 'authenticate') reply({});
  else if (m.method === 'session/new') reply({sessionId:'fake-session',configOptions:[{id:'model',name:'Model',category:'model',type:'select',currentValue:'fake-model',options:[{value:'fake-model',name:'Fake model'}]}]});
  else if (m.method === 'session/prompt') {
    const text = m.params.prompt.filter(x=>x.type==='text').map(x=>x.text).join('\n');
    const toolId = 'working-copy';
    const target = join(process.cwd(),'notes.md');
    update({sessionUpdate:'tool_call',toolCallId:toolId,title:'Write working notes',kind:'edit',status:'pending',locations:[{path:target}]});
    const id = `permission-${m.id}`;
    pending.set(id,{m,text,toolId,target});
    send({id,method:'session/request_permission',params:{sessionId:'fake-session',toolCall:{toolCallId:toolId,title:'Write working notes',kind:'edit',status:'pending',locations:[{path:target}]},options:[{optionId:'allow_once',name:'Allow once',kind:'allow_once'},{optionId:'reject_once',name:'Reject',kind:'reject_once'}]}});
  } else if (m.method === 'session/cancel') {
    for (const {m:request} of pending.values()) send({id:request.id,result:{stopReason:'cancelled'}});
    pending.clear();
  } else if (pending.has(m.id)) {
    const {m:request,text,toolId,target} = pending.get(m.id); pending.delete(m.id);
    if (m.result?.outcome?.optionId === 'allow_once') await appendFile(target,'Working copy tool completed\n');
    update({sessionUpdate:'tool_call_update',toolCallId:toolId,status:m.result?.outcome?.optionId==='allow_once'?'completed':'failed'});
    const docId = text.match(/"(?:id|document_id)"\s*:\s*"([0-9a-f-]{36})"/)?.[1];
    const result = text.includes('"findings"') ? {findings:docId?[{document_id:docId,severity:'warning',dimension:'continuity',message:'Check the harbor clock.',suggestion:'Keep the clock consistent.'}]:[]} : text.includes('"candidates"') ? {candidates:[{kind:'character',title:'Mira',aliases:[],summary:'Mira keeps the harbor notebook.'}]} : {chapter_markdown:'# Harbor\n\nMira opened the gate and wrote the time in her notebook. The harbor lamps still burned above the empty road. She counted the boats one by one, looking for the blue sail her brother had promised to raise. When the tide turned, a small vessel came around the headland. Its captain held up a dry notebook, and Mira recognized the red thread she had tied around its cover. She took the rope he threw across the water and secured it to the iron ring. Neither spoke until the boat rested against the quay. Then he told her that the storm had passed, and that he had come home.'};
    const json = JSON.stringify(result);
    for (let i=0; i<json.length; i+=23) { update({sessionUpdate:'agent_message_chunk',content:{type:'text',text:json.slice(i,i+23)}}); await new Promise(r=>setTimeout(r,5)); }
    send({id:request.id,result:{stopReason:'end_turn',usage:{inputTokens:120,outputTokens:36}}});
  }
}

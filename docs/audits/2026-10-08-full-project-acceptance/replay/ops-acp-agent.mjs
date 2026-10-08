import { createInterface } from 'node:readline';
import { appendFile } from 'node:fs/promises';
import { join } from 'node:path';
const pending = new Map();
const send = message => process.stdout.write(JSON.stringify({ jsonrpc:'2.0', ...message })+'\n');
for await (const line of createInterface({ input:process.stdin })) {
  const message = JSON.parse(line);
  const reply = result => send({ id:message.id,result });
  if(message.method==='initialize') reply({ protocolVersion:1, agentCapabilities:{},authMethods:[{id:'cached_token',name:'Synthetic cached auth'}] });
  else if(message.method==='authenticate') reply({});
  else if(message.method==='session/new') reply({ sessionId:'ops-session',configOptions:[{id:'model',name:'Model',category:'model',type:'select',currentValue:'ops-fake-model',options:[{value:'ops-fake-model',name:'Synthetic model'}]}] });
  else if(message.method==='session/prompt') {
    const target=join(process.cwd(),'notes.md');
    send({method:'session/update',params:{sessionId:'ops-session',update:{sessionUpdate:'tool_call',toolCallId:'ops-write',title:'Write synthetic material notes',kind:'edit',status:'pending',locations:[{path:target}]}}});
    pending.set('ops-permission',message.id);
    send({id:'ops-permission',method:'session/request_permission',params:{sessionId:'ops-session',toolCall:{toolCallId:'ops-write',title:'Write synthetic material notes',kind:'edit',status:'pending',locations:[{path:target}]},options:[{optionId:'allow_once',name:'Allow synthetic write once',kind:'allow_once'},{optionId:'reject_once',name:'Reject',kind:'reject_once'}]}});
  } else if(pending.has(message.id)) {
    const id=pending.get(message.id);pending.delete(message.id);
    if(message.result?.outcome?.optionId!=='allow_once') { send({id,result:{stopReason:'cancelled'}});continue; }
    await appendFile(join(process.cwd(),'notes.md'),'Synthetic container-to-host ACP material write completed.\n');
    send({method:'session/update',params:{sessionId:'ops-session',update:{sessionUpdate:'tool_call_update',toolCallId:'ops-write',status:'completed'}}});
    send({method:'session/update',params:{sessionId:'ops-session',update:{sessionUpdate:'agent_message_chunk',content:{type:'text',text:JSON.stringify({chapter_markdown:'# 合成 ACP 提议\n\n'+'合成任务文字用于验证工作副本和正式书稿相互独立。'.repeat(45)})}}}});
    send({id,result:{stopReason:'end_turn',usage:{inputTokens:120,outputTokens:350}}});
  } else if(message.method==='session/cancel') { for(const id of pending.values())send({id,result:{stopReason:'cancelled'}});pending.clear(); }
}

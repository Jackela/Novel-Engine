import {execFileSync as replayGit} from 'node:child_process';
import { pathToFileURL as replayFileUrl } from 'node:url';
const replayRoot=process.env.NOVEL_ENGINE_REPLAY_ROOT ?? process.cwd();
const replayCandidateSha=replayGit('git',['-C',replayRoot,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const replayEvidence=process.env.NOVEL_ENGINE_REPLAY_EVIDENCE;

import { writeFile } from 'node:fs/promises';
const { AcpGateway }=await import(replayFileUrl(replayRoot+"/server/dist/shared/interface/acp/AcpGateway.js").href);
const { AcpAgentProcess }=await import(replayFileUrl(replayRoot+"/server/dist/shared/infrastructure/acp/AcpAgentProcess.js").href);
const { AcpTokenFile }=await import(replayFileUrl(replayRoot+"/server/dist/shared/infrastructure/acp/AcpTokenFile.js").href);
const token = await AcpTokenFile(process.argv[2], { create: true });
const gateway = new AcpGateway({ token, launchAgent: AcpAgentProcess.launch, diagnostic: (message) => console.error(message) });
const address = await gateway.listen({ host: '0.0.0.0', port: 0 });
await writeFile(process.argv[3], JSON.stringify(address));
process.on('SIGTERM', async () => { await gateway.close(); process.exitCode = 0; });
process.on('SIGINT', async () => { await gateway.close(); process.exitCode = 0; });

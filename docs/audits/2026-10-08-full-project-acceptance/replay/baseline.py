"""Rebuild the fixed baseline and replay three expected acceptance failures in isolated data."""
from pathlib import Path
import io, os, subprocess, tarfile, tempfile
root = Path(os.environ.get('NOVEL_ENGINE_REPLAY_ROOT', os.getcwd())).resolve()
output = Path(os.environ['NOVEL_ENGINE_REPLAY_EVIDENCE']).resolve()
output.mkdir(parents=True, exist_ok=True)
workspace = Path(tempfile.mkdtemp(prefix='ne-baseline-replay-'))
archive = subprocess.check_output(['git', '-C', str(root), 'archive', '066d923d8bb92a47c7d6a12d8352b2aa471cbd4b'])
with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
    allowed = [m for m in bundle.getmembers() if not (any(p.startswith('.env') for p in Path(m.name).parts) or m.name.startswith(('data/', 'config/env/')) or Path(m.name).name in ('AUDIT_REPORT_Linus.md', 'Makefile', 'justfile'))]
    bundle.extractall(workspace, members=allowed, filter='data')
(workspace/'server/node_modules').symlink_to(root/'server/node_modules', target_is_directory=True)
source = (Path(__file__).parent/'baseline.template.ts').read_text()
source = source.replace('__BASELINE__', str(workspace)).replace('__OUTPUT__', str(output))
(output/'baseline.test.ts').write_text(source)
config = output/'vitest.config.mjs'
config.write_text('export default '+repr({'test': {'environment':'node','include':[str(output/'baseline.test.ts')],'maxWorkers':1,'testTimeout':30000}}).replace("'",'"')+';\n')
print('baseline source:', workspace, flush=True)
with (output/'baseline.log').open('w') as log:
    result = subprocess.run(['pnpm','--dir',str(workspace/'server'),'exec','vitest','run','--config',str(config)], stdout=log, stderr=subprocess.STDOUT)
print('Result:', result.returncode, '; expected three failures until the reported bugs are fixed. See', output/'baseline.log')
raise SystemExit(result.returncode)

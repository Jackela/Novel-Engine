# Tasks

- [x] 1. Tag `python-final` on the pre-cutover main and protect it
- [x] 2. Regenerate the OpenAPI baseline from the TS server and review the
      diff against the Python snapshot (equals the adjudicated set; the
      single-document GET route removed per #277 adjudication)
- [x] 3. Pivot frontend codegen to the TS baseline and drop the dual-stack
      parsing branches
- [x] 4. Remove the Python tree, Alembic, Python tests/scripts, and Python
      root configuration in the confirmed inventory
- [x] 5. Switch compose/Dockerfile to the single TS image with the Node
      healthcheck on `/health/ready`
- [x] 6. Rewrite README, Makefile, justfile, and `.env.example` for
      pnpm/Node operations
- [x] 7. Retire the Python CI jobs (validate steps, python-freeze,
      pip-audit, CodeQL python) and the Python-bound e2e smoke stack
- [x] 8. Move the release-version authority to `server/package.json`
      (`0.4.0`)
- [x] 9. Carry the six pure-frontend Requirements verbatim into
      `novel-engine` and retire `novel-studio`
- [x] 10. Close #240 as superseded-by-adjudication; release v0.4.0 with the
       one-way data door stated in the notes

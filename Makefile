.PHONY: install validate test frontend build serve doctor

install:
	uv sync --extra dev --extra test
	corepack pnpm install --frozen-lockfile

validate:
	uv run python scripts/qa/check_ssot.py
	uv run python scripts/qa/check_repo_hygiene.py
	corepack pnpm spec:validate

test:
	uv run pytest -q

frontend:
	corepack pnpm --dir frontend type-check
	corepack pnpm --dir frontend test:unit

build:
	corepack pnpm --dir frontend build

serve:
	uv run novel-engine serve --reload

doctor:
	uv run novel-engine doctor

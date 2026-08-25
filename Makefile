.PHONY: install validate test frontend validate-frontend build e2e-smoke serve doctor

install:
	pnpm install --frozen-lockfile

validate:
	pnpm --dir server gates
	pnpm --dir server type-check
	pnpm --dir server lint
	pnpm --dir server arch
	pnpm --dir server test
	pnpm spec:validate

test:
	pnpm --dir server test

frontend:
	pnpm --dir frontend lint
	pnpm --dir frontend format:check
	pnpm --dir frontend type-check
	pnpm --dir frontend test:unit

validate-frontend: frontend build

build:
	pnpm --dir frontend build
	pnpm --dir server build

e2e-smoke:
	pnpm --dir frontend test:e2e:smoke

serve:
	pnpm --dir server cli serve

doctor:
	pnpm --dir server cli doctor

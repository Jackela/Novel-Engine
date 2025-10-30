## QA Tooling Entities

- **FormattingPolicy**: Defines formatter versions (Black/isort), includes target paths, exclude patterns, and enforcement script entry point.
- **LintConfig**: Aggregates Flake8/Mypy settings, ignore rules, and type-check targets.
- **RegressionTestSuite**: Catalog of high-priority tests (integration/unit), status flags (pass/skip/xfail), and owner notes.
- **ToolingEnvironment**: Captures virtualenv path, Playwright browser cache, Docker/act prerequisites.

### Relationships
- FormattingPolicy feeds into LintConfig (shared exclusions).
- RegressionTestSuite references ToolingEnvironment metadata (requirements to run tests locally/CI).

### Validation Rules
- Every policy must specify version pins and compatible Python versions.
- RegressionTestSuite entries require documented rationale for skip/xfail states.

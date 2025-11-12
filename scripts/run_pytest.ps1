$ErrorActionPreference = "Stop"
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "UTF-8"
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Error "venv missing"; exit 2 }
# Use -n auto for parallel execution (auto-detect CPU count)
# Remove -n flag if you need serial execution for debugging
& $py -m pytest -n auto -q -rA --junitxml=pytest-report.xml --color=no -p asyncio -p timeout @Args
exit $LASTEXITCODE

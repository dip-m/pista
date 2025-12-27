# Backend test runner script for Windows
# Usage: .\scripts\run_backend_tests.ps1 [pytest-args]

$env:LANGCHAIN_TRACING_V2 = "false"
$env:LANGCHAIN_ENDPOINT = ""

python -m pytest -p no:langsmith $args

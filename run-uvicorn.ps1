# Simple wrapper to run uvicorn with proper exclusions
# Usage: .\run-uvicorn.ps1

# Set environment variable to exclude directories from watchfiles
$env:WATCHFILES_IGNORE_PATHS = "venv;venv/;venv\;venv/**;venv\**;.git;.git/;.git\;.git/**;.git\**;__pycache__;__pycache__/;__pycache__\;__pycache__/**;__pycache__\**;*.pyc;gen;gen/;gen\;gen/**;gen\**;logs;logs/;logs\;logs/**;logs\**;node_modules;node_modules/;node_modules\;node_modules/**;node_modules\**"

# Run uvicorn with exclusions
# Note: main.py is now in backend/, so use backend.main:app
python -m uvicorn backend.main:app --reload `
    --reload-exclude "venv" `
    --reload-exclude "venv/**" `
    --reload-exclude "venv/*" `
    --reload-exclude ".git" `
    --reload-exclude ".git/**" `
    --reload-exclude "__pycache__" `
    --reload-exclude "__pycache__/**" `
    --reload-exclude "*.pyc" `
    --reload-exclude "gen" `
    --reload-exclude "gen/**" `
    --reload-exclude "logs" `
    --reload-exclude "logs/**" `
    --reload-exclude "node_modules" `
    --reload-exclude "node_modules/**"


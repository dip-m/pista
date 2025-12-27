#!/bin/bash
# Backend test runner script that disables problematic plugins
# Usage: ./scripts/run_backend_tests.sh [pytest-args]

export LANGCHAIN_TRACING_V2=false
export LANGCHAIN_ENDPOINT=""

python -m pytest -p no:langsmith "$@"

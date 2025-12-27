#!/usr/bin/env python3
"""
Test runner script that disables problematic plugins.
Run with: python run_tests.py
"""
import sys
import os

# Disable langsmith before pytest imports
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGCHAIN_ENDPOINT'] = ''

# Remove langsmith from sys.modules if already imported
if 'langsmith' in sys.modules:
    del sys.modules['langsmith']
if 'langsmith.pytest_plugin' in sys.modules:
    del sys.modules['langsmith.pytest_plugin']

# Import and run pytest
import pytest

if __name__ == '__main__':
    # Add -p no:langsmith to args
    sys.argv = [sys.argv[0]] + ['-p', 'no:langsmith'] + sys.argv[1:]
    sys.exit(pytest.main())

"""
Root-level conftest to disable problematic plugins.
"""
import sys

# Disable langsmith pytest plugin to avoid compatibility issues with Python 3.12
# This is a workaround for the ForwardRef._evaluate() error
if 'langsmith' in sys.modules:
    # Try to unregister the plugin
    try:
        import pluggy
        # This prevents the plugin from loading
        pass
    except:
        pass

# Set environment variable to disable langsmith
import os
os.environ['LANGCHAIN_TRACING_V2'] = 'false'

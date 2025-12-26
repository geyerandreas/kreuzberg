#!/bin/bash
set -e
echo "Running mypy type checking on main.py..."
uvx mypy main.py --strict
echo "✓ Type checking passed"

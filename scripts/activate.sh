#!/bin/bash
# Pixi environment activation script
# This script is sourced when the pixi environment is activated

echo "🚀 LLM Task Framework - Pixi Environment Activated"
echo "📦 Project: $(pixi info --json | jq -r '.project_info.name')"
echo "🐍 Python: $(python --version)"
echo "📍 Environment: $(pixi info --json | jq -r '.project_info.environments[0]')"
echo ""
echo "🔧 Available tasks:"
echo "  pixi run test         - Run test suite"
echo "  pixi run check        - Full quality checks"
echo "  pixi run docs-serve   - Serve documentation"
echo "  pixi run security-all - Security scans"
echo ""
echo "💡 Use 'pixi task list' to see all available tasks"
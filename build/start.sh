#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="$PATH:$HOME/Library/Android/sdk/platform-tools"
"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/app.py"

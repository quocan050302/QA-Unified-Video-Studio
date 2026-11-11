#!/bin/bash
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  python3 app.py --open
elif command -v python >/dev/null 2>&1; then
  python app.py --open
else
  echo "Python 3 is required. Install it first."
  read -r -p 'Press Enter to close...'
fi

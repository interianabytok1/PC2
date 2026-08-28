#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install -r requirements.txt
python3 build.py
echo "Aplikacia je v priecinku release."
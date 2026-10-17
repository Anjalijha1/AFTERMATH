#!/bin/sh
set -eu
cd "$(dirname "$0")"
python -m compileall -q app
python -m pytest -q

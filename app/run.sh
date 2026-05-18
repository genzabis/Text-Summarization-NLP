#!/usr/bin/env bash
# Helper untuk menjalankan server di Linux/macOS
set -e
cd "$(dirname "$0")/.."
python -m app.backend.app

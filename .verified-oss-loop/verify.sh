#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
python3 -m pytest -q
(cd site && npm test && npm run build)
echo "verified-oss-loop: python + lookdev tests passed"

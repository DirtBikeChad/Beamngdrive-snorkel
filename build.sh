#!/usr/bin/env bash
# Packages the mod into dist/UniversalSnorkel.zip with the correct BeamNG
# layout (lua/ and scripts/ at the top level of the zip).
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p dist
rm -f dist/UniversalSnorkel.zip

if command -v zip >/dev/null 2>&1; then
  zip -r dist/UniversalSnorkel.zip lua scripts -x '*.DS_Store'
else
  python3 - <<'PY'
import os, zipfile
with zipfile.ZipFile('dist/UniversalSnorkel.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for top in ('lua', 'scripts'):
        for root, _, files in os.walk(top):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, p)
PY
fi

echo "Built dist/UniversalSnorkel.zip"

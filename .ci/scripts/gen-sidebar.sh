#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
[ -d node_modules ] || npm install
node .vitepress/scripts/print-sidebar.mjs

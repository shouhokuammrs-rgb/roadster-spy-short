#!/bin/bash
# 全カットをレンダー（2 本ずつ並行）。usage: bash render_all.sh [cut ...]
cd "$(dirname "$0")"
CUTS=${@:-$(python3 -c "import json;print(' '.join(c['id'] for c in json.load(open('blocking.json'))['cuts']))")}
printf "%s\n" $CUTS | xargs -P 2 -I{} sh -c 'python3 render_blocking.py -- blocking.json {} out/ > out/{}.log 2>&1 && echo "{} ok" || echo "{} FAIL"'

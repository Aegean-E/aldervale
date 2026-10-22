#!/bin/sh
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
    exec python3 -m aldervale "$@"
fi
if command -v python >/dev/null 2>&1; then
    exec python -m aldervale "$@"
fi
echo "ALDERVALE needs Python 3.10 or newer." >&2
exit 1

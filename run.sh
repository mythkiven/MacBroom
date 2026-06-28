#!/usr/bin/env bash
# MacBroom 启动脚本（免安装直跑）：优先使用 python，回退 python3。
set -e
cd "$(dirname "$0")"

if command -v python >/dev/null 2>&1; then
  PY=python
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  echo "未找到 Python 3，请先安装。" >&2
  exit 1
fi

exec "$PY" -m macbroom "$@"

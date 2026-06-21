#!/bin/sh
set -e

mkdir -p /app/config /app/input /app/workspace /app/logs

# 首次启动：在挂载目录生成默认 .env（宿主机 ./config/.env 可持久化编辑）
if [ ! -f /app/config/.env ]; then
  cp /app/.env.example /app/config/.env
fi
ln -sf /app/config/.env /app/.env

# 若宿主机 ./src / ./frontend 为空目录挂载，用镜像内备份恢复（避免空挂载盖住镜像内容）
if [ ! -f /app/src/reggraph_assistant/__init__.py ]; then
  cp -a /app/.image_backup/src/. /app/src/
fi
if [ ! -f /app/frontend/static/index.html ]; then
  cp -a /app/.image_backup/frontend/. /app/frontend/
fi

if [ "$#" -eq 0 ]; then
  set -- serve
fi

exec reggraph-assistant "$@"

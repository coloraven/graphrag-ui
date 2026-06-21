#!/bin/sh
set -e

mkdir -p /app/input /app/workspace /app/logs

if [ "$#" -eq 0 ]; then
  set -- serve
fi

exec reggraph-assistant "$@"

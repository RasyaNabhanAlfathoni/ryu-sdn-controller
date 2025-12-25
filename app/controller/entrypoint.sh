#!/bin/sh
set -e

echo "RYU Controller starting"
echo "WSGI Port: ${CONTROLLER_PORT}"

exec ryu-manager \
  --wsapi-port ${CONTROLLER_PORT} \
  /opt/sdn-controller/controller.py
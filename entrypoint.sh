#!/bin/sh

echo "Registering service in Consul..."

# wait for consul to be ready (because life is never synchronous)
until python - <<EOF
import urllib.request
try:
    urllib.request.urlopen("http://consul:8500/v1/status/leader")
except:
    raise SystemExit(1)
EOF
do
  sleep 1
done
HOST_IP=$(hostname -i)

python - <<EOF
import requests, os

requests.put(
    "http://consul:8500/v1/agent/service/register",
    json={
            "name": "shopping_cart",
            "address": "shopping_cart",
            "port": 8002,
            "check": {
                "http": "http://shopping_cart:8002/health/",
                "interval": "10s"
                    }
    }
)
EOF

echo "Starting Gunicorn..."

exec gunicorn --bind 0.0.0.0:8002 shopping_cart.wsgi:application
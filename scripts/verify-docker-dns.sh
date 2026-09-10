#!/usr/bin/env bash
set -euo pipefail
API="${API:-http://localhost:8000}"

echo "=== verify-dns: API from host ==="
curl -sf "$API/healthz" | python3 -m json.tool

echo "=== verify-dns: causeway-api container resolves github.com ==="
if docker compose exec -T causeway-api python3 -c "
import socket
socket.getaddrinfo('github.com', 443)
print('dns_ok')
" 2>/dev/null; then
  :
else
  echo "dns_warn: container DNS check failed (see scripts/setup-wsl-dns.sh)"
  exit 1
fi

echo "verify_dns_ok"

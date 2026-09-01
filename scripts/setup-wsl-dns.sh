#!/usr/bin/env bash
# Fix WSL DNS when /etc/wsl.conf has generateResolvConf=false but resolv.conf is missing.
# Run once from WSL (as root):  wsl -u root bash scripts/setup-wsl-dns.sh
# Or:  sudo bash scripts/setup-wsl-dns.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run with sudo or: wsl -u root bash scripts/setup-wsl-dns.sh" >&2
  exit 1
fi

mkdir -p /etc
cat >/etc/wsl.conf <<'EOF'
[network]
generateResolvConf = false
EOF

# Prefer Windows/router DNS (works on corporate/home LAN), then public + Docker Desktop.
# Detect default gateway as first nameserver when available.
GW="$(ip route 2>/dev/null | awk '/^default/ {print $3; exit}')"
{
  if [[ -n "${GW:-}" ]]; then
    echo "nameserver ${GW}"
  fi
  echo "nameserver 1.1.1.1"
  echo "nameserver 8.8.8.8"
  echo "nameserver 192.168.65.7"
} >/etc/resolv.conf
chmod 644 /etc/resolv.conf

echo "Wrote /etc/wsl.conf and /etc/resolv.conf:"
cat /etc/resolv.conf
echo
echo "Quick check:"
getent hosts github.com || echo "WARNING: github.com still does not resolve"
echo
echo "If resolution still fails after reboot, from PowerShell run: wsl --shutdown"
echo "then reopen WSL and re-run this script."

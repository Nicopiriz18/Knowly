#!/usr/bin/env bash
# One-time setup for a fresh Ubuntu 24.04 Hetzner server. Run as root:
#   bash deploy/setup-server.sh
set -euo pipefail

apt-get update
apt-get upgrade -y
apt-get install -y ca-certificates curl git ufw unattended-upgrades

# Docker Engine + compose plugin
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi

# Firewall: SSH and web only
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable

# 2 GB swap so builds and video processing don't run out of memory
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Automatic security updates
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "Listo. Docker $(docker --version)"

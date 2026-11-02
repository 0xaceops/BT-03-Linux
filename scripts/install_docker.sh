#!/usr/bin/env bash
# Chay tren MOI VM Ubuntu Server:  bash scripts/install_docker.sh
set -e
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
curl -fsSL https://tailscale.com/install.sh | sudo sh
echo ">> Xong. Dang xuat/dang nhap lai, roi chay: sudo tailscale up   (cung 1 tai khoan/tailnet cho ca nhom)"

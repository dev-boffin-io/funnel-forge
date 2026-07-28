#!/bin/bash

echo -e "\e[1;31m=== Stopping Share-Forge Tailscale Funnel ===\e[0m"

# 1. Stop all Tailscale and Funnel processes
echo -e "\e[1;33mKilling Tailscale processes...\e[0m"
sudo pkill tailscale 2>/dev/null
sudo pkill tailscaled 2>/dev/null

# 2. Remove the socket file (so the port doesn't stay locked)
sudo rm -f /tmp/tailscaled.sock

echo -e "\e[1;32mTailscale daemon and Funnel stopped successfully!\e[0m"

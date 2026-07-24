#!/bin/bash

echo -e "\e[1;31m=== Stopping Funnel-Forge ===\e[0m"

echo -e "\e[1;33mKilling Tailscale processes...\e[0m"
sudo pkill tailscale 2>/dev/null
sudo pkill tailscaled 2>/dev/null
sudo rm -f /tmp/tailscaled.sock

echo -e "\e[1;32mTailscale daemon and Funnel stopped successfully.\e[0m"

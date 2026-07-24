#!/bin/bash

echo -e "\e[1;34m=== Starting Funnel-Forge ===\e[0m"

sudo pkill tailscaled 2>/dev/null
sudo rm -f /tmp/tailscaled.sock

echo -e "\e[1;33mInitializing Tailscale daemon...\e[0m"
sudo tailscaled --tun=userspace-networking --socket=/tmp/tailscaled.sock > /dev/null 2>&1 &
sleep 3

echo -e "\e[1;33mConnecting to Tailscale network...\e[0m"
sudo tailscale --socket=/tmp/tailscaled.sock up --hostname=share-forge > /dev/null 2>&1

echo -e "\e[1;32mStarting Funnel on port 5000...\e[0m"
sudo tailscale --socket=/tmp/tailscaled.sock funnel 5000

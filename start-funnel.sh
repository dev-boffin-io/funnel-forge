#!/bin/bash

echo -e "\e[1;34m=== Restarting Share-Forge Tailscale Funnel ===\e[0m"

# 1. Clean up any old socket and background process
sudo pkill tailscaled 2>/dev/null
sudo rm -f /tmp/tailscaled.sock

# 2. Start the Tailscale daemon in the background
echo -e "\e[1;33mStarting Tailscale daemon...\e[0m"
sudo tailscaled --tun=userspace-networking --socket=/tmp/tailscaled.sock > /dev/null 2>&1 &
sleep 3

# 3. Reconnect to the Tailscale network
echo -e "\e[1;34mConnecting to network...\e[0m"
sudo tailscale --socket=/tmp/tailscaled.sock up --hostname=boffin-io > /dev/null 2>&1

# 4. Launch the funnel on port 3000
echo -e "\e[1;32mLaunching Funnel on port 3000...\e[0m"
sudo tailscale --socket=/tmp/tailscaled.sock funnel 3000

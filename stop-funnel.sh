#!/bin/bash

echo -e "\e[1;31m=== Stopping Share-Forge Tailscale Funnel ===\e[0m"

# ১. Tailscale এবং Funnel এর সকল প্রসেস বন্ধ করা
echo -e "\e[1;33mKilling Tailscale processes...\e[0m"
sudo pkill tailscale 2>/dev/null
sudo pkill tailscaled 2>/dev/null

# ২. সকেট ফাইল মুছে ফেলা (যাতে পোর্ট লক না থাকে)
sudo rm -f /tmp/tailscaled.sock

echo -e "\e[1;32mTailscale daemon and Funnel stopped successfully!\e[0m"

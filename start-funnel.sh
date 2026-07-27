#!/bin/bash

echo -e "\e[1;34m=== Restarting Share-Forge Tailscale Funnel ===\e[0m"

# ১. পুরোনো সকেট এবং ব্যাকগ্রাউন্ড প্রসেস ক্লিন করা
sudo pkill tailscaled 2>/dev/null
sudo rm -f /tmp/tailscaled.sock

# ২. ব্যাকগ্রাউন্ডে Tailscale ডেমন চালু করা
echo -e "\e[1;33mStarting Tailscale daemon...\e[0m"
sudo tailscaled --tun=userspace-networking --socket=/tmp/tailscaled.sock > /dev/null 2>&1 &
sleep 3

# ৩. টেইলস্কেল নেটওয়ার্কে রি-কানেক্ট করা
echo -e "\e[1;34mConnecting to network...\e[0m"
sudo tailscale --socket=/tmp/tailscaled.sock up --hostname=boffin-io > /dev/null 2>&1

# ৪. পোর্ট ৫০০০ এর জন্য ফানেল চালু করা
echo -e "\e[1;32mLaunching Funnel on port 3000...\e[0m"
sudo tailscale --socket=/tmp/tailscaled.sock funnel 3000

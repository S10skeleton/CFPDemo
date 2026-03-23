#!/bin/bash
# Run this with: sudo bash ~/setup_autoboot.sh

echo "Setting up passwordless shutdown for s10skeleton..."

# Add sudoers rule (safe method using tee)
echo "s10skeleton ALL=(ALL) NOPASSWD: /sbin/shutdown, /sbin/reboot" | sudo tee /etc/sudoers.d/s10skeleton-shutdown > /dev/null

# Fix permissions
sudo chmod 0440 /etc/sudoers.d/s10skeleton-shutdown

echo "✓ Sudoers configured"
echo "✓ Shutdown will now work without password"
echo ""
echo "Still need to do manually:"
echo "1. Run: sudo raspi-config"
echo "2. Go to: System Options → Boot / Auto Login → Console Autologin"
echo "3. Reboot and the UI should auto-launch!"

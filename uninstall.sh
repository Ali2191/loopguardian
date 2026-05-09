#!/bin/bash

# LoopGuardian Uninstallation Script for macOS
# Complete removal script with service cleanup and configuration backup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}   LoopGuardian Uninstaller v0.1.0   ${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
}

# Function to prompt user for confirmation
prompt_yes_no() {
    local prompt="$1"
    local default="${2:-n}"
    
    while true; do
        if [[ "$default" == "y" ]]; then
            read -p "$prompt [Y/n]: " response
            response=${response:-y}
        else
            read -p "$prompt [y/N]: " response
            response=${response:-n}
        fi
        
        case $response in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

# Function to backup configuration
backup_config() {
    local source_dir="$1"
    local backup_dir="$2"
    
    if [[ -d "$source_dir" ]]; then
        print_status "Creating backup of configuration..."
        mkdir -p "$backup_dir"
        cp -r "$source_dir"/* "$backup_dir/" 2>/dev/null || true
        print_status "Configuration backed up to: $backup_dir"
    fi
}

# Main uninstallation starts here
print_header

print_status "LoopGuardian Uninstaller"
print_status "This script will completely remove LoopGuardian from your system."
echo ""

# Check if LoopGuard is installed
install_dir="$HOME/.loopguardian"
if [[ ! -d "$install_dir" ]]; then
    print_warning "LoopGuardian installation not found at $install_dir"
    if ! prompt_yes_no "Continue anyway?" "n"; then
        print_status "Uninstallation cancelled."
        exit 0
    fi
fi

# Show what will be removed
echo ""
print_status "The following will be removed:"
echo "   • Installation directory: $install_dir"
echo "   • Command: /usr/local/bin/loopguardian (if exists)"
echo "   • Command: $HOME/.local/bin/loopguardian (if exists)"
echo "   • Launch service: ~/Library/LaunchAgents/com.loopguardian.agent.plist"
echo "   • All logs and data files"
echo ""

# Backup option
backup_config_dir="$HOME/loopguardian-backup-$(date +%Y%m%d-%H%M%S)"
if prompt_yes_no "Create backup of configuration before uninstalling?" "y"; then
    backup_config "$install_dir" "$backup_config_dir"
fi

# Confirmation
echo ""
print_warning "This will permanently remove LoopGuardian from your system."
if ! prompt_yes_no "Are you sure you want to uninstall LoopGuardian?" "n"; then
    print_status "Uninstallation cancelled."
    exit 0
fi

# Stop and remove launchd service
print_status "Stopping and removing launchd service..."

plist_file="$HOME/Library/LaunchAgents/com.loopguardian.agent.plist"
if [[ -f "$plist_file" ]]; then
    # Unload the service
    if launchctl list | grep -q "com.loopguardian.agent"; then
        print_status "Stopping LoopGuardian service..."
        launchctl stop "com.loopguardian.agent" 2>/dev/null || true
    fi
    
    # Unload the service
    print_status "Unloading LoopGuardian service..."
    launchctl unload "$plist_file" 2>/dev/null || true
    
    # Remove the plist file
    print_status "Removing service configuration..."
    rm -f "$plist_file"
else
    print_status "No launchd service found."
fi

# Also check for old service name
old_plist_file="$HOME/Library/LaunchAgents/com.loopguardian.plist"
if [[ -f "$old_plist_file" ]]; then
    print_status "Removing old service configuration..."
    launchctl stop "com.loopguardian" 2>/dev/null || true
    launchctl unload "$old_plist_file" 2>/dev/null || true
    rm -f "$old_plist_file"
fi

# Remove command wrappers
print_status "Removing command wrappers..."

# Remove from /usr/local/bin
if [[ -f "/usr/local/bin/loopguardian" ]]; then
    print_status "Removing /usr/local/bin/loopguardian..."
    if [[ -w "/usr/local/bin" ]]; then
        rm -f "/usr/local/bin/loopguardian"
    else
        print_warning "Cannot remove /usr/local/bin/loopguardian (permission denied)"
        print_warning "Please run: sudo rm -f /usr/local/bin/loopguardian"
    fi
fi

# Remove from ~/.local/bin
if [[ -f "$HOME/.local/bin/loopguardian" ]]; then
    print_status "Removing $HOME/.local/bin/loopguardian..."
    rm -f "$HOME/.local/bin/loopguardian"
fi

# Remove installation directory
if [[ -d "$install_dir" ]]; then
    print_status "Removing installation directory..."
    rm -rf "$install_dir"
else
    print_status "Installation directory not found."
fi

# Clean up PATH modifications
print_status "Checking for PATH modifications..."

# Check .zshrc
zshrc_file="$HOME/.zshrc"
if [[ -f "$zshrc_file" ]]; then
    if grep -q "loopguardian" "$zshrc_file" 2>/dev/null; then
        print_status "Removing LoopGuardian PATH from .zshrc..."
        # Create backup
        cp "$zshrc_file" "$zshrc_file.loopguardian-backup"
        # Remove loopguard lines
        sed -i.tmp '/loopguardian/d' "$zshrc_file" 2>/dev/null || true
        rm -f "$zshrc_file.tmp"
        print_status "Backup created: $zshrc_file.loopguardian-backup"
    fi
fi

# Check .bash_profile
bash_profile="$HOME/.bash_profile"
if [[ -f "$bash_profile" ]]; then
    if grep -q "loopguardian" "$bash_profile" 2>/dev/null; then
        print_status "Removing LoopGuardian PATH from .bash_profile..."
        cp "$bash_profile" "$bash_profile.loopguardian-backup"
        sed -i.tmp '/loopguardian/d' "$bash_profile" 2>/dev/null || true
        rm -f "$bash_profile.tmp"
        print_status "Backup created: $bash_profile.loopguardian-backup"
    fi
fi

# Clean up any remaining processes
print_status "Checking for running LoopGuardian processes..."
if pgrep -f "loopguardian" > /dev/null 2>&1; then
    print_warning "Found running LoopGuardian processes. Terminating..."
    pkill -f "loopguardian" 2>/dev/null || true
    sleep 2
    # Force kill if still running
    pkill -9 -f "loopguardian" 2>/dev/null || true
fi

# Remove any temporary files
print_status "Cleaning up temporary files..."
rm -rf /tmp/loopguardian-* 2>/dev/null || true
rm -rf /var/tmp/loopguardian-* 2>/dev/null || true

# Final verification
print_status "Verifying removal..."

# Check if command still exists
if command -v loopguardian &> /dev/null; then
    print_warning "LoopGuardian command still found in PATH"
    print_warning "You may need to restart your terminal or manually remove the command"
else
    print_status "✅ LoopGuardian command successfully removed"
fi

# Check if service still loaded
if launchctl list | grep -q "loopguardian"; then
    print_warning "LoopGuardian service still loaded"
    print_warning "You may need to restart your system or run: launchctl remove com.loopguardian.agent"
else
    print_status "✅ LoopGuardian service successfully removed"
fi

# Check if installation directory still exists
if [[ -d "$install_dir" ]]; then
    print_warning "Installation directory still exists"
    print_warning "You may need to manually remove: $install_dir"
else
    print_status "✅ Installation directory successfully removed"
fi

# Uninstallation complete
echo ""
print_header
print_status "🎉 LoopGuardian uninstallation completed successfully!"
echo ""

if [[ -n "$backup_config_dir" && -d "$backup_config_dir" ]]; then
    echo "📦 Configuration backup created at:"
    echo "   • $backup_config_dir"
    echo ""
    echo "💡 To restore your configuration later:"
    echo "   • Reinstall LoopGuardian"
    echo "   • Copy files from backup to ~/.loopguardian/"
    echo ""
fi

echo "🧹 Additional cleanup you may want to perform:"
echo "   • Restart your terminal to refresh PATH"
echo "   • Restart your system to ensure all services are stopped"
echo "   • Remove any manual PATH modifications you added"
echo ""

echo "📝 Thank you for trying LoopGuardian!"
echo "   • We'd appreciate feedback: https://github.com/loopguard/loopguard/issues"
echo "   • Consider reinstalling in the future!"
echo ""

print_status "LoopGuardian has been completely removed from your system. 👋"

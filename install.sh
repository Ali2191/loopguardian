#!/bin/bash

# LoopGuardian Installation Script for macOS
# Interactive installer with service registration and PATH setup

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
    echo -e "${BLUE}   LoopGuardian Installer v0.1.0   ${NC}"
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

# Function to detect Claude Code installation
detect_claude_code() {
    local claude_paths=(
        "$HOME/Applications/Claude.app"
        "/Applications/Claude.app"
        "/usr/local/bin/claude"
        "$HOME/.local/bin/claude"
    )
    
    for path in "${claude_paths[@]}"; do
        if [[ -e "$path" ]]; then
            echo "$path"
            return 0
        fi
    done
    
    return 1
}

# Main installation starts here
print_header

print_status "Welcome to LoopGuardian! This installer will set up LoopGuardian for automatic loop detection in Claude Code."
echo ""

# Check if already installed
if [[ -d "$HOME/.loopguardian" ]]; then
    print_warning "LoopGuardian appears to be already installed at $HOME/.loopguardian"
    if ! prompt_yes_no "Do you want to reinstall/upgrade LoopGuardian?" "n"; then
        print_status "Installation cancelled."
        exit 0
    fi
    print_status "Removing existing installation..."
    rm -rf "$HOME/.loopguardian"
fi

# System requirements check
print_status "Checking system requirements..."

# Check macOS version
if [[ $(uname) != "Darwin" ]]; then
    print_error "LoopGuardian is designed for macOS. Current OS: $(uname)"
    exit 1
fi

# Check Python 3
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    print_status "Please install Python 3 from https://python.org or via Homebrew"
    exit 1
fi

python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
print_status "Found Python $python_version"

# Check pip
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is required but not installed"
    print_status "Please install pip3: python3 -m ensurepip --upgrade"
    exit 1
fi

# Check Homebrew and offer to install terminal-notifier
if ! command -v brew &> /dev/null; then
    print_warning "Homebrew not found. Desktop notifications require terminal-notifier."
    if prompt_yes_no "Install Homebrew first?" "n"; then
        print_status "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        print_warning "Skipping desktop notifications. You can install terminal-notifier later."
    fi
fi

# Detect Claude Code
claude_path=$(detect_claude_code)
if [[ $? -eq 0 ]]; then
    print_status "Found Claude Code at: $claude_path"
else
    print_warning "Claude Code not detected. LoopGuardian will work but you may need to specify paths manually."
fi

# Installation options
echo ""
print_status "Installation options:"

# Installation directory
default_install_dir="$HOME/.loopguardian"
read -p "Installation directory [$default_install_dir]: " install_dir
install_dir=${install_dir:-$default_install_dir}

# Auto-start service
auto_start=true
if ! prompt_yes_no "Enable automatic startup on login?" "y"; then
    auto_start=false
fi

# Desktop notifications
notifications=true
if command -v terminal-notifier &> /dev/null; then
    if ! prompt_yes_no "Enable desktop notifications?" "y"; then
        notifications=false
    fi
else
    if prompt_yes_no "Install terminal-notifier for desktop notifications?" "y"; then
        if command -v brew &> /dev/null; then
            brew install terminal-notifier
        else
            print_warning "Skipping terminal-notifier installation (Homebrew not available)"
            notifications=false
        fi
    else
        notifications=false
    fi
fi

# Start installation
echo ""
print_status "Starting installation..."

# Create installation directory
mkdir -p "$install_dir"
mkdir -p "$install_dir/logs"
mkdir -p "$install_dir/config"

# Create virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv "$install_dir/venv"

# Activate virtual environment and install LoopGuard
print_status "Installing LoopGuardian package..."
source "$install_dir/venv/bin/activate"
pip install --upgrade pip
pip install watchdog>=3.0.0 psutil>=5.9.0 click>=8.0.0 jsonschema>=4.0.0

# Create command wrapper
print_status "Creating loopguardian command..."
if [[ -w "/usr/local/bin" ]]; then
    # Try to install in /usr/local/bin if writable
    cat > /usr/local/bin/loopguardian << EOF
#!/bin/bash
source "$install_dir/venv/bin/activate"
python -m loopguard.cli "\$@"
EOF
    chmod +x /usr/local/bin/loopguardian
    command_path="/usr/local/bin/loopguardian"
else
    # Use user's local bin directory
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/loopguardian" << EOF
#!/bin/bash
source "$install_dir/venv/bin/activate"
python -m loopguard.cli "\$@"
EOF
    chmod +x "$HOME/.local/bin/loopguardian"
    command_path="$HOME/.local/bin/loopguardian"
    
    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bash_profile"
        print_warning "Added $HOME/.local/bin to PATH. Please restart your terminal or run: source ~/.zshrc"
    fi
fi

# Create configuration
print_status "Creating default configuration..."
config_file="$install_dir/config/config.yaml"
cat > "$config_file" << EOF
# LoopGuardian Configuration
detection:
  tool_call_repeats: 3
  error_repeats: 2
  stagnation_minutes: 5
  session_timeout_minutes: 30

monitoring:
  claude_code_path: "$claude_path"
  watch_directories:
    - "$HOME/Desktop"
    - "$HOME/Documents"
    - "$HOME/Downloads"
  file_patterns:
    - "*.py"
    - "*.js"
    - "*.ts"
    - "*.jsx"
    - "*.tsx"
    - "*.md"

notifications:
  enabled: $notifications
  throttle_seconds: 30
  sound: true
  desktop: true

logging:
  level: INFO
  max_file_size_mb: 10
  backup_count: 5
EOF

# Setup launchd service if requested
if [[ "$auto_start" == "true" ]]; then
    print_status "Setting up automatic startup service..."
    
    plist_file="$HOME/Library/LaunchAgents/com.loopguardian.agent.plist"
    python_path="$install_dir/venv/bin/python"
    
    cat > "$plist_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loopguardian.agent</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$python_path</string>
        <string>-m</string>
        <string>loopguard.cli</string>
        <string>monitor</string>
        <string>--config</string>
        <string>$config_file</string>
        <string>--daemon</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$HOME</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>NetworkState</key>
        <true/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>$install_dir/logs/loopguardian.log</string>
    
    <key>StandardErrorPath</key>
    <string>$install_dir/logs/loopguardian.error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>LOOPGUARDIAN_HOME</key>
        <string>$install_dir</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    
    <key>StartInterval</key>
    <integer>300</integer>
    
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
EOF
    
    # Load the launchd service
    launchctl load "$plist_file"
    print_status "Service loaded. LoopGuardian will start automatically on login."
fi

# Test installation
print_status "Testing installation..."
if command -v loopguardian &> /dev/null; then
    print_status "✅ LoopGuardian command is available"
else
    print_error "❌ LoopGuardian command not found in PATH"
fi

# Installation complete
echo ""
print_header
print_status "🎉 LoopGuardian installation completed successfully!"
echo ""
echo "📋 Quick Start:"
echo "   • Command: $command_path"
echo "   • Config: $config_file"
echo "   • Logs: $install_dir/logs/"
echo ""

if [[ "$auto_start" == "true" ]]; then
    echo "� Service Status:"
    echo "   • Auto-start: Enabled"
    echo "   • Start now: launchctl start com.loopguardian.agent"
    echo "   • Stop: launchctl stop com.loopguardian.agent"
    echo ""
fi

echo "🔧 Common Commands:"
echo "   • Check status: loopguardian status"
echo "   • Test notifications: loopguardian test"
echo "   • View logs: tail -f $install_dir/logs/loopguardian.log"
echo "   • Edit config: nano $config_file"
echo ""

echo "� Documentation:"
echo "   • User Guide: https://loopguard.readthedocs.io/"
echo "   • Issues: https://github.com/loopguard/loopguard/issues"
echo ""

if [[ "$notifications" == "true" ]]; then
    print_status "Testing desktop notification..."
    if command -v terminal-notifier &> /dev/null; then
        terminal-notifier -title "LoopGuardian" -message "Installation completed successfully!" -sound default
    fi
fi

print_status "Thank you for installing LoopGuardian! 🛡️"

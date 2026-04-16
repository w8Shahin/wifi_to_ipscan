#!/bin/bash

# W8IP-To Router - Auto Installation Script
# Author: W8Team / W8SOJIB
# GitHub: github.com/W8SOJIB

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Banner
clear
echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║                   W8IP-To Router - Installer                         ║"
echo "║                                                                      ║"
echo "║              Advanced IP Scanner & Router Detector                   ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "${YELLOW}Version: 2.0 - Ultra Fast Edition${NC}"
echo -e "${GREEN}Author: W8Team / W8SOJIB${NC}"
echo -e "${CYAN}GitHub: github.com/W8SOJIB${NC}"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Detect OS
detect_os() {
    if [ -f /data/data/com.termux/files/home ]; then
        OS="termux"
        echo -e "${GREEN}[+] Detected: Termux (Android)${NC}"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        echo -e "${GREEN}[+] Detected: Linux${NC}"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="mac"
        echo -e "${GREEN}[+] Detected: macOS${NC}"
    else
        OS="unknown"
        echo -e "${YELLOW}[!] Unknown OS detected${NC}"
    fi
}

# Check Python installation
check_python() {
    echo -e "${CYAN}[*] Checking Python installation...${NC}"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        echo -e "${GREEN}[+] Python3 found: ${PYTHON_VERSION}${NC}"
        PYTHON_CMD="python3"
        return 0
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
        echo -e "${GREEN}[+] Python found: ${PYTHON_VERSION}${NC}"
        PYTHON_CMD="python"
        return 0
    else
        echo -e "${RED}[!] Python not found!${NC}"
        return 1
    fi
}

# Install Python (Termux)
install_python_termux() {
    echo -e "${YELLOW}[*] Installing Python for Termux...${NC}"
    pkg update -y
    pkg install python -y
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[+] Python installed successfully!${NC}"
        return 0
    else
        echo -e "${RED}[!] Failed to install Python${NC}"
        return 1
    fi
}

# Install Python (Linux)
install_python_linux() {
    echo -e "${YELLOW}[*] Installing Python for Linux...${NC}"
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install python3 python3-pip -y
    elif command -v yum &> /dev/null; then
        sudo yum install python3 python3-pip -y
    elif command -v dnf &> /dev/null; then
        sudo dnf install python3 python3-pip -y
    else
        echo -e "${RED}[!] Package manager not found. Please install Python manually.${NC}"
        return 1
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[+] Python installed successfully!${NC}"
        return 0
    else
        echo -e "${RED}[!] Failed to install Python${NC}"
        return 1
    fi
}

# Install required tools
install_tools() {
    echo -e "${CYAN}[*] Installing required system tools...${NC}"
    
    if [ "$OS" == "termux" ]; then
        pkg install net-tools iproute2 -y
    elif [ "$OS" == "linux" ]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get install net-tools iproute2 -y
        fi
    fi
    
    echo -e "${GREEN}[+] System tools installed${NC}"
}

# Create launcher script
create_launcher() {
    echo -e "${CYAN}[*] Creating launcher script...${NC}"
    
    if [ "$OS" == "termux" ]; then
        LAUNCHER_PATH="$PREFIX/bin/w8ip"
    else
        LAUNCHER_PATH="$HOME/.local/bin/w8ip"
        mkdir -p "$HOME/.local/bin"
    fi
    
    cat > "$LAUNCHER_PATH" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/W8IP-To-Router-Scanner.py" "$@"
EOF
    
    chmod +x "$LAUNCHER_PATH"
    
    # Make sure W8IP-To-Router-Scanner.py is executable
    chmod +x W8IP-To-Router-Scanner.py
    
    echo -e "${GREEN}[+] Launcher created: ${LAUNCHER_PATH}${NC}"
}

# Add to PATH
add_to_path() {
    if [ "$OS" == "termux" ]; then
        echo -e "${GREEN}[+] Termux automatically includes $PREFIX/bin in PATH${NC}"
    else
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
            echo -e "${GREEN}[+] Added to PATH in ~/.bashrc${NC}"
            echo -e "${YELLOW}[!] Run 'source ~/.bashrc' or restart terminal${NC}"
        fi
    fi
}

# Main installation
main() {
    echo -e "${BOLD}${CYAN}Starting installation...${NC}\n"
    
    # Detect OS
    detect_os
    echo ""
    
    # Check Python
    if ! check_python; then
        echo -e "${YELLOW}[*] Python not found. Installing...${NC}"
        
        if [ "$OS" == "termux" ]; then
            install_python_termux
        elif [ "$OS" == "linux" ]; then
            install_python_linux
        else
            echo -e "${RED}[!] Please install Python manually${NC}"
            exit 1
        fi
        
        # Check again after installation
        if ! check_python; then
            echo -e "${RED}[!] Installation failed${NC}"
            exit 1
        fi
    fi
    
    echo ""
    
    # Install required tools
    install_tools
    echo ""
    
    # Create launcher
    create_launcher
    echo ""
    
    # Add to PATH
    add_to_path
    echo ""
    
    # Installation complete
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${GREEN}✓ Installation Complete!${NC}\n"
    echo -e "${CYAN}Usage:${NC}"
    echo -e "  ${YELLOW}Method 1:${NC} python3 W8IP-To-Router-Scanner.py"
    echo -e "  ${YELLOW}Method 2:${NC} ./W8IP-To-Router-Scanner.py"
    if [ "$OS" == "termux" ]; then
        echo -e "  ${YELLOW}Method 3:${NC} w8ip"
    fi
    echo ""
    echo -e "${CYAN}Features:${NC}"
    echo -e "  ${GREEN}•${NC} Ultra-fast multi-threaded scanning"
    echo -e "  ${GREEN}•${NC} Device detection & identification"
    echo -e "  ${GREEN}•${NC} MAC address & manufacturer lookup"
    echo -e "  ${GREEN}•${NC} WiFi router detection"
    echo -e "  ${GREEN}•${NC} Public & private IP display"
    echo -e "  ${GREEN}•${NC} Auto-save results to TXT file"
    echo ""
    echo -e "${YELLOW}Example:${NC}"
    echo -e "  Scan range: python3 W8IP-To-Router-Scanner.py"
    echo -e "  Then enter: 192.168.1.1 to 192.168.1.254"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Tool by: ${BOLD}W8Team / W8SOJIB${NC}"
    echo -e "${CYAN}GitHub: github.com/W8SOJIB${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Run installation
main

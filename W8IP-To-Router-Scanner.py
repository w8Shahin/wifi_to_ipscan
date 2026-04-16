#!/usr/bin/env python3
"""
W8IP-To Router - Advanced IP Scanner
Fast multi-threaded scanner for IP ranges - ports 80 and 8080
Shows detailed device information including MAC, manufacturer, NetBIOS, etc.
Supports Windows, Linux, Termux (Android)

Author: W8Team / W8SOJIB
Tool: W8IP-To Router
"""

import socket
import sys
import ipaddress
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import subprocess
import re
import platform
import os
import itertools

# ANSI Color codes for better display
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def is_termux():
    """Check if running on Termux"""
    return os.path.exists('/data/data/com.termux') or 'TERMUX_VERSION' in os.environ

def clear_screen():
    """Clear terminal screen"""
    if is_termux() or platform.system() != "Windows":
        os.system('clear')
    else:
        os.system('cls')

def get_network_interfaces():
    """Get all network interface IP addresses including WLAN"""
    interfaces = {}
    
    try:
        if platform.system() == "Windows":
            # Use ipconfig on Windows
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=3)
            output = result.stdout
            
            current_adapter = None
            for line in output.split('\n'):
                # Detect adapter name
                if "adapter" in line.lower() and ":" in line:
                    current_adapter = line.split(':')[0].strip()
                    if "wireless" in current_adapter.lower() or "wi-fi" in current_adapter.lower():
                        current_adapter = "WLAN"
                    elif "ethernet" in current_adapter.lower():
                        current_adapter = "Ethernet"
                    else:
                        current_adapter = None
                
                # Extract IPv4 address
                if current_adapter and "IPv4" in line:
                    ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                    if ip_match:
                        interfaces[current_adapter] = ip_match.group(1)
        
        elif is_termux():
            # For Termux/Android - use ip command
            result = subprocess.run(['ip', 'addr'], capture_output=True, text=True, timeout=3)
            output = result.stdout
            
            current_interface = None
            for line in output.split('\n'):
                # Detect interface name
                if line and not line.startswith(' '):
                    if 'wlan' in line.lower():
                        current_interface = "WLAN"
                    elif 'eth' in line.lower():
                        current_interface = "Ethernet"
                    else:
                        current_interface = None
                
                # Extract IP address
                if current_interface and 'inet ' in line:
                    ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', line)
                    if ip_match:
                        ip = ip_match.group(1)
                        if ip != "127.0.0.1":  # Skip localhost
                            interfaces[current_interface] = ip
        
        else:
            # For Linux/Mac - use ip or ifconfig
            try:
                result = subprocess.run(['ip', 'addr'], capture_output=True, text=True, timeout=3)
                output = result.stdout
                
                current_interface = None
                for line in output.split('\n'):
                    if line and not line.startswith(' '):
                        if 'wlan' in line.lower() or 'wlp' in line.lower():
                            current_interface = "WLAN"
                        elif 'eth' in line.lower() or 'enp' in line.lower():
                            current_interface = "Ethernet"
                        else:
                            current_interface = None
                    
                    if current_interface and 'inet ' in line:
                        ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', line)
                        if ip_match:
                            ip = ip_match.group(1)
                            if ip != "127.0.0.1":
                                interfaces[current_interface] = ip
            except:
                # Fallback to ifconfig
                result = subprocess.run(['ifconfig'], capture_output=True, text=True, timeout=3)
                output = result.stdout
                
                current_interface = None
                for line in output.split('\n'):
                    if line and not line.startswith(' '):
                        if 'wlan' in line.lower():
                            current_interface = "WLAN"
                        elif 'eth' in line.lower():
                            current_interface = "Ethernet"
                    
                    if current_interface and 'inet ' in line:
                        ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', line)
                        if ip_match:
                            ip = ip_match.group(1)
                            if ip != "127.0.0.1":
                                interfaces[current_interface] = ip
    
    except:
        pass
    
    # If no interfaces found, try simple method
    if not interfaces:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            own_ip = s.getsockname()[0]
            s.close()
            interfaces["Primary"] = own_ip
        except:
            try:
                hostname = socket.gethostname()
                own_ip = socket.gethostbyname(hostname)
                interfaces["Primary"] = own_ip
            except:
                interfaces["Unknown"] = "Not Available"
    
    return interfaces

def get_default_gateway():
    """Get default gateway/router IP address"""
    try:
        if platform.system() == "Windows":
            # Use route print on Windows
            result = subprocess.run(['route', 'print', '0.0.0.0'], capture_output=True, text=True, timeout=3)
            output = result.stdout
            
            # Find default gateway
            for line in output.split('\n'):
                if '0.0.0.0' in line:
                    parts = line.split()
                    for part in parts:
                        if re.match(r'\d+\.\d+\.\d+\.\d+', part) and part != '0.0.0.0':
                            return part
        
        elif is_termux():
            # For Termux/Android
            result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=3)
            output = result.stdout
            
            for line in output.split('\n'):
                if 'default' in line:
                    match = re.search(r'via (\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        return match.group(1)
        
        else:
            # For Linux/Mac
            result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=3)
            output = result.stdout
            
            for line in output.split('\n'):
                if 'default' in line:
                    match = re.search(r'via (\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        return match.group(1)
            
            # Fallback to route command
            result = subprocess.run(['route', '-n'], capture_output=True, text=True, timeout=3)
            output = result.stdout
            
            for line in output.split('\n'):
                if line.startswith('0.0.0.0'):
                    parts = line.split()
                    if len(parts) > 1:
                        return parts[1]
    
    except:
        pass
    
    return "Not Found"

def get_public_ip():
    """Get public IP address using external API"""
    try:
        # Try multiple services for reliability
        services = [
            'https://api.ipify.org',
            'https://icanhazip.com',
            'https://ifconfig.me/ip',
        ]
        
        for service in services:
            try:
                import urllib.request
                with urllib.request.urlopen(service, timeout=5) as response:
                    public_ip = response.read().decode('utf-8').strip()
                    # Validate IP format
                    if re.match(r'\d+\.\d+\.\d+\.\d+', public_ip):
                        return public_ip
            except:
                continue
        
        return "Not Available"
    except:
        return "Not Available"

def get_current_datetime():
    """Get current date and time in 12-hour format"""
    now = datetime.now()
    date_str = now.strftime("%B %d, %Y")  # e.g., "October 15, 2025"
    time_str = now.strftime("%I:%M:%S %p")  # e.g., "02:30:45 PM"
    return date_str, time_str

def print_banner():
    """Display tool banner"""
    banner = f"""{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   ██╗    ██╗ █████╗ ██╗██████╗       ████████╗ ██████╗              ║
║   ██║    ██║██╔══██╗██║██╔══██╗      ╚══██╔══╝██╔═══██╗             ║
║   ██║ █╗ ██║╚█████╔╝██║██████╔╝ █████╗  ██║   ██║   ██║             ║
║   ██║███╗██║██╔══██╗██║██╔═══╝  ╚════╝  ██║   ██║   ██║             ║
║   ╚███╔███╔╝╚█████╔╝██║██║              ██║   ╚██████╔╝             ║
║    ╚══╝╚══╝  ╚════╝ ╚═╝╚═╝              ╚═╝    ╚═════╝              ║
║                                                                      ║
║              ██████╗  ██████╗ ██╗   ██╗████████╗███████╗██████╗     ║
║              ██╔══██╗██╔═══██╗██║   ██║╚══██╔══╝██╔════╝██╔══██╗    ║
║              ██████╔╝██║   ██║██║   ██║   ██║   █████╗  ██████╔╝    ║
║              ██╔══██╗██║   ██║██║   ██║   ██║   ██╔══╝  ██╔══██╗    ║
║              ██║  ██║╚██████╔╝╚██████╔╝   ██║   ███████╗██║  ██║    ║
║              ╚═╝  ╚═╝ ╚═════╝  ╚═════╝    ╚═╝   ╚══════╝╚═╝  ╚═╝    ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
{Colors.ENDC}"""
    
    info = f"""{Colors.YELLOW}
┌──────────────────────────────────────────────────────────────────────┐
│  {Colors.BOLD}Tool Name:{Colors.ENDC}{Colors.YELLOW}     W8IP-To Router - Advanced IP Scanner                │
│  {Colors.BOLD}Version:{Colors.ENDC}{Colors.YELLOW}       2.0 - Ultra Fast Edition                            │
│  {Colors.BOLD}Author:{Colors.ENDC}{Colors.YELLOW}        W8Team / W8SOJIB                                     │
│  {Colors.BOLD}GitHub:{Colors.ENDC}{Colors.YELLOW}        github.com/W8SOJIB                                    │
│  {Colors.BOLD}Features:{Colors.ENDC}{Colors.YELLOW}      Multi-threaded Scanning, Device Detection           │
│                MAC/Manufacturer Lookup, Router Detection            │
└──────────────────────────────────────────────────────────────────────┘
{Colors.ENDC}"""
    
    # Get system information
    platform_info = f"{Colors.GREEN}[+] Platform: {platform.system()}"
    if is_termux():
        platform_info += f" (Termux - Android){Colors.ENDC}"
    else:
        platform_info += f"{Colors.ENDC}"
    
    # Get network interfaces
    interfaces = get_network_interfaces()
    
    # Get gateway and public IP
    gateway_ip = get_default_gateway()
    print(f"{Colors.CYAN}[*] Detecting public IP...{Colors.ENDC}", end='\r')
    public_ip = get_public_ip()
    print(' ' * 40, end='\r')  # Clear the detection message
    
    # Get current date and time
    date_str, time_str = get_current_datetime()
    
    print(banner)
    print(info)
    print(platform_info)
    print(f"{Colors.GREEN}[+] Python Version: {sys.version.split()[0]}{Colors.ENDC}")
    
    # Display network interfaces
    print(f"\n{Colors.BOLD}{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.YELLOW}                    NETWORK INFORMATION{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
    
    # Local IP Addresses
    if interfaces:
        print(f"\n{Colors.BOLD}{Colors.GREEN}LOCAL IP ADDRESSES:{Colors.ENDC}")
        for interface_name, ip_address in interfaces.items():
            if interface_name == "WLAN":
                # Highlight WLAN interface
                print(f"  {Colors.GREEN}╰─➤{Colors.ENDC} {Colors.BOLD}{Colors.YELLOW}WLAN (WiFi):{Colors.ENDC}  {Colors.BOLD}{Colors.CYAN}{ip_address}{Colors.ENDC}")
            elif interface_name == "Ethernet":
                print(f"  {Colors.GREEN}╰─➤{Colors.ENDC} {Colors.BOLD}Ethernet:{Colors.ENDC}     {Colors.CYAN}{ip_address}{Colors.ENDC}")
            else:
                print(f"  {Colors.GREEN}╰─➤{Colors.ENDC} {Colors.BOLD}{interface_name}:{Colors.ENDC}         {Colors.CYAN}{ip_address}{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}[!] No network interfaces detected{Colors.ENDC}")
    
    # Gateway/Router IP
    print(f"\n{Colors.BOLD}{Colors.GREEN}ROUTER/GATEWAY:{Colors.ENDC}")
    if gateway_ip != "Not Found":
        print(f"  {Colors.GREEN}╰─➤{Colors.ENDC} {Colors.BOLD}{Colors.YELLOW}Default Gateway:{Colors.ENDC} {Colors.BOLD}{Colors.CYAN}{gateway_ip}{Colors.ENDC} {Colors.GREEN}(Your Router){Colors.ENDC}")
    else:
        print(f"  {Colors.YELLOW}╰─➤ Gateway IP not detected{Colors.ENDC}")
    
    # Public IP
    print(f"\n{Colors.BOLD}{Colors.GREEN}PUBLIC IP ADDRESS:{Colors.ENDC}")
    if public_ip != "Not Available":
        print(f"  {Colors.GREEN}╰─➤{Colors.ENDC} {Colors.BOLD}{Colors.YELLOW}Public IP:{Colors.ENDC}       {Colors.BOLD}{Colors.BLUE}{public_ip}{Colors.ENDC} {Colors.CYAN}(Internet IP){Colors.ENDC}")
    else:
        print(f"  {Colors.YELLOW}╰─➤ Public IP not available (Check internet connection){Colors.ENDC}")
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
    print(f"{Colors.GREEN}[+] Current Date: {Colors.YELLOW}{date_str}{Colors.ENDC}")
    print(f"{Colors.GREEN}[+] Current Time: {Colors.YELLOW}{time_str}{Colors.ENDC}")
    print()

def get_mac_address(ip):
    """
    Get MAC address for an IP using ARP (Windows/Linux/Termux compatible)
    
    Args:
        ip (str): IP address
    
    Returns:
        str: MAC address or "Unknown"
    """
    try:
        if platform.system() == "Windows":
            # Use arp -a on Windows
            result = subprocess.run(['arp', '-a', ip], capture_output=True, text=True, timeout=2)
            output = result.stdout
            
            # Parse MAC address from output
            mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
            match = re.search(mac_pattern, output)
            if match:
                return match.group(0).upper().replace('-', ':')
        else:
            # Use arp on Linux/Mac/Termux
            # First try to ping to populate ARP cache
            subprocess.run(['ping', '-c', '1', '-W', '1', ip], capture_output=True, timeout=2)
            
            # Try ip neigh (newer Linux/Termux)
            result = subprocess.run(['ip', 'neigh', 'show', ip], capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout:
                mac_pattern = r'([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}'
                match = re.search(mac_pattern, result.stdout)
                if match:
                    return match.group(0).upper()
            
            # Fallback to arp command
            result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True, timeout=2)
            output = result.stdout
            
            mac_pattern = r'([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}'
            match = re.search(mac_pattern, output)
            if match:
                return match.group(0).upper()
    except:
        pass
    return "Unknown"

def get_manufacturer(mac):
    """
    Get manufacturer from MAC address OUI (first 3 bytes)
    
    Args:
        mac (str): MAC address
    
    Returns:
        str: Manufacturer name
    """
    if mac == "Unknown" or not mac:
        return "Unknown"
    
    # Common OUI database (partial - add more as needed)
    oui_database = {
        '00:50:56': 'VMware',
        '00:0C:29': 'VMware',
        '00:05:69': 'VMware',
        '00:1C:42': 'VMware',
        '00:1D:D8': 'TP-Link',
        '00:23:CD': 'TP-Link',
        '50:C7:BF': 'TP-Link',
        'A4:2B:B0': 'TP-Link',
        'EC:08:6B': 'TP-Link',
        '00:1F:3C': 'Netgear',
        '00:1E:2A': 'Netgear',
        '00:26:F2': 'Netgear',
        '00:03:7F': 'D-Link',
        '00:05:5D': 'D-Link',
        '00:0D:88': 'D-Link',
        '00:17:9A': 'D-Link',
        '00:1B:11': 'D-Link',
        '00:15:E9': 'D-Link',
        '00:50:BA': 'D-Link',
        '00:80:C8': 'D-Link',
        '28:10:7B': 'D-Link',
        '00:13:46': 'Cisco',
        '00:1E:13': 'Cisco',
        '00:23:04': 'Cisco',
        '00:1A:A1': 'Cisco',
        '00:03:E3': 'Cisco',
        '00:0E:83': 'Cisco',
        '00:18:0A': 'Cisco',
        '00:1C:58': 'Cisco',
        '00:1D:71': 'Cisco',
        '00:24:13': 'Cisco',
        '00:25:84': 'Cisco',
        '00:26:0A': 'Cisco',
        '00:0A:95': 'Apple',
        '00:0D:93': 'Apple',
        '00:14:51': 'Apple',
        '00:16:CB': 'Apple',
        '00:17:F2': 'Apple',
        '00:19:E3': 'Apple',
        '00:1B:63': 'Apple',
        '00:1C:B3': 'Apple',
        '00:1D:4F': 'Apple',
        '00:1E:52': 'Apple',
        '00:1F:5B': 'Apple',
        '00:1F:F3': 'Apple',
        '00:21:E9': 'Apple',
        '00:22:41': 'Apple',
        '00:23:12': 'Apple',
        '00:23:32': 'Apple',
        '00:23:6C': 'Apple',
        '00:23:DF': 'Apple',
        '00:24:36': 'Apple',
        '00:25:00': 'Apple',
        '00:25:4B': 'Apple',
        '00:25:BC': 'Apple',
        '00:26:08': 'Apple',
        '00:26:4A': 'Apple',
        '00:26:B0': 'Apple',
        '00:26:BB': 'Apple',
        '00:03:93': 'Apple',
        '00:05:02': 'Apple',
        '00:0A:27': 'Apple',
        '00:0C:41': 'Asus',
        '00:15:F2': 'Asus',
        '00:17:31': 'Asus',
        '00:1A:92': 'Asus',
        '00:1E:8C': 'Asus',
        '00:22:15': 'Asus',
        '00:23:54': 'Asus',
        '00:24:8C': 'Asus',
        '00:26:18': 'Asus',
        '08:00:27': 'Oracle VirtualBox',
        '00:E0:4C': 'Realtek',
        '00:01:6C': 'Realtek',
        '52:54:00': 'QEMU/KVM',
        '00:16:3E': 'Xen',
        '00:15:5D': 'Microsoft Hyper-V',
        '00:19:99': 'Fujitsu',
        '00:21:CC': 'Huawei',
        '00:25:9E': 'Huawei',
        '00:E0:FC': 'Huawei',
        '28:6E:D4': 'Huawei',
        '34:6B:D3': 'Huawei',
        '00:11:32': 'Synology',
        '00:0B:82': 'Grandstream',
        '00:1F:C6': 'Linksys',
        '00:12:17': 'Linksys',
        '00:13:10': 'Linksys',
        '00:14:BF': 'Linksys',
        '00:18:39': 'Linksys',
        '00:18:F8': 'Linksys',
        '00:1A:70': 'Linksys',
        '00:1C:10': 'Linksys',
        '00:1D:7E': 'Linksys',
        '00:1E:E5': 'Linksys',
        '00:20:E0': 'Linksys',
        '00:21:29': 'Linksys',
        '00:22:6B': 'Linksys',
        '00:23:69': 'Linksys',
        '00:25:9C': 'Linksys',
        '68:7F:74': 'Linksys',
        'C0:C1:C0': 'Linksys',
    }
    
    # Extract OUI (first 3 bytes)
    oui = ':'.join(mac.split(':')[:3]).upper()
    
    return oui_database.get(oui, "Unknown")

def get_netbios_name(ip):
    """
    Get NetBIOS name using nbtstat (Windows) or nmblookup (Linux)
    
    Args:
        ip (str): IP address
    
    Returns:
        str: NetBIOS name or "Unknown"
    """
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['nbtstat', '-A', ip], capture_output=True, text=True, timeout=2)
            output = result.stdout
            
            # Parse NetBIOS name from output
            lines = output.split('\n')
            for line in lines:
                if '<00>' in line and 'UNIQUE' in line:
                    # Extract computer name
                    name = line.split()[0].strip()
                    if name and not name.startswith('_'):
                        return name
        else:
            # Try nmblookup on Linux
            result = subprocess.run(['nmblookup', '-A', ip], capture_output=True, text=True, timeout=2)
            output = result.stdout
            
            lines = output.split('\n')
            for line in lines:
                if '<00>' in line:
                    name = line.split()[0].strip()
                    if name:
                        return name
    except:
        pass
    return "Unknown"

def get_hostname(ip):
    """
    Try to resolve hostname for an IP address
    
    Args:
        ip (str): IP address
    
    Returns:
        str: Hostname or "Unknown" if not resolvable
    """
    try:
        hostname = socket.gethostbyaddr(ip)[0]
        return hostname
    except:
        return "Unknown"

def detect_device_type(hostname, mac, manufacturer, open_ports):
    """
    Detect device type based on available information
    
    Args:
        hostname (str): Device hostname
        mac (str): MAC address
        manufacturer (str): Manufacturer name
        open_ports (list): List of open ports
    
    Returns:
        str: Device type
    """
    hostname_lower = hostname.lower() if hostname != "Unknown" else ""
    manufacturer_lower = manufacturer.lower() if manufacturer != "Unknown" else ""
    
    # Router detection
    router_keywords = ['router', 'gateway', 'rt-', 'wrt', 'archer', 'asus', 'netgear', 'linksys', 'dlink', 'tplink']
    if any(keyword in hostname_lower for keyword in router_keywords):
        return "Router/Gateway"
    if any(keyword in manufacturer_lower for keyword in ['tp-link', 'netgear', 'd-link', 'linksys', 'asus', 'cisco']):
        return "Router/Gateway"
    
    # Server detection
    if 'server' in hostname_lower or any(p['port'] in [80, 8080, 443, 8443] for p in open_ports):
        return "Web Server"
    
    # VM detection
    vm_manufacturers = ['vmware', 'virtualbox', 'qemu', 'xen', 'hyper-v']
    if any(vm in manufacturer_lower for vm in vm_manufacturers):
        return "Virtual Machine"
    
    # NAS detection
    if 'nas' in hostname_lower or 'synology' in manufacturer_lower:
        return "NAS/Storage"
    
    # Default
    return "Computer/Device"

def scan_port(ip, port, timeout=0.3):
    """
    Scan a single port on the given IP address (ultra-optimized for speed)
    
    Args:
        ip (str): IP address to scan
        port (int): Port number to scan
        timeout (int): Connection timeout in seconds
    
    Returns:
        tuple: (is_open, response_time_ms)
    """
    try:
        # Create a socket object with optimized settings
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        
        # Time the connection attempt
        start_time = time.time()
        result = sock.connect_ex((ip, port))
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except:
            pass
        sock.close()
        
        # If result is 0, connection was successful (port is open)
        if result == 0:
            return (True, response_time)
        return (False, 0)
    except:
        # Any connection errors
        return (False, 0)

def validate_ip(ip):
    """
    Validate if the given string is a valid IP address
    
    Args:
        ip (str): IP address string to validate
    
    Returns:
        bool: True if valid IP, False otherwise
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def ip_to_int(ip):
    """
    Convert IP address string to integer
    
    Args:
        ip (str): IP address string
    
    Returns:
        int: IP address as integer
    """
    return int(ipaddress.ip_address(ip))

def int_to_ip(ip_int):
    """
    Convert integer to IP address string
    
    Args:
        ip_int (int): IP address as integer
    
    Returns:
        str: IP address string
    """
    return str(ipaddress.ip_address(ip_int))

def generate_ip_range(start_ip, end_ip):
    """
    Generate list of IP addresses between start and end IP
    
    Args:
        start_ip (str): Starting IP address
        end_ip (str): Ending IP address
    
    Returns:
        list: List of IP addresses in the range
    """
    start_int = ip_to_int(start_ip)
    end_int = ip_to_int(end_ip)
    
    if start_int > end_int:
        start_int, end_int = end_int, start_int
    
    return [int_to_ip(ip_int) for ip_int in range(start_int, end_int + 1)]

def get_ttl_info(ip):
    """
    Get TTL (Time To Live) information which can hint at OS type
    
    Args:
        ip (str): IP address
    
    Returns:
        tuple: (ttl_value, os_guess)
    """
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['ping', '-n', '1', ip], capture_output=True, text=True, timeout=2)
        else:
            result = subprocess.run(['ping', '-c', '1', ip], capture_output=True, text=True, timeout=2)
        
        output = result.stdout
        ttl_match = re.search(r'[Tt][Tt][Ll]=(\d+)', output)
        
        if ttl_match:
            ttl = int(ttl_match.group(1))
            # Common TTL values and OS detection
            if ttl <= 64:
                os_guess = "Linux/Unix/Android"
            elif ttl <= 128:
                os_guess = "Windows"
            else:
                os_guess = "Cisco/Router"
            return (ttl, os_guess)
    except:
        pass
    return (None, "Unknown")

def scan_single_ip(ip_address, ports_to_scan):
    """
    Scan a single IP address for open ports with detailed info
    
    Args:
        ip_address (str): IP address to scan
        ports_to_scan (list): List of ports to scan
    
    Returns:
        dict: Comprehensive scan results
    """
    result = {
        'ip': ip_address,
        'hostname': None,
        'netbios': None,
        'mac': None,
        'manufacturer': None,
        'device_type': None,
        'user': None,
        'ttl': None,
        'os_guess': None,
        'open_ports': []
    }
    
    port_info = []
    
    for port in ports_to_scan:
        is_open, response_time = scan_port(ip_address, port)
        if is_open:
            port_info.append({
                'port': port,
                'response_time': response_time
            })
    
    # Only get detailed info if we found open ports (saves time)
    if port_info:
        result['hostname'] = get_hostname(ip_address)
        result['netbios'] = get_netbios_name(ip_address)
        result['mac'] = get_mac_address(ip_address)
        result['manufacturer'] = get_manufacturer(result['mac'])
        result['device_type'] = detect_device_type(result['hostname'], result['mac'], result['manufacturer'], port_info)
        
        # Get TTL and OS guess
        ttl, os_guess = get_ttl_info(ip_address)
        result['ttl'] = ttl
        result['os_guess'] = os_guess
        
        # Extract user from NetBIOS or hostname if available
        if result['netbios'] and result['netbios'] != "Unknown":
            result['user'] = result['netbios']
        elif result['hostname'] and result['hostname'] != "Unknown":
            # Try to extract username from hostname
            result['user'] = result['hostname'].split('.')[0]
        else:
            result['user'] = "Unknown"
        
        result['open_ports'] = port_info
    
    return result

def save_results_to_file(found_devices, start_ip, end_ip, total_scanned, scan_start_time):
    """
    Save scan results to a text file
    
    Args:
        found_devices (list): List of devices found
        start_ip (str): Starting IP
        end_ip (str): Ending IP
        total_scanned (int): Total hosts scanned
        scan_start_time (str): When scan started
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"W8IP_Scan_Results_{timestamp}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # Header
            f.write("="*70 + "\n")
            f.write("W8IP-To Router - Network Scan Results\n")
            f.write("="*70 + "\n")
            f.write(f"Tool: W8IP-To Router v2.0\n")
            f.write(f"Author: W8Team / W8SOJIB\n")
            f.write(f"Scan Date: {datetime.now().strftime('%B %d, %Y at %I:%M:%S %p')}\n")
            f.write(f"IP Range: {start_ip} - {end_ip}\n")
            f.write(f"Total Hosts Scanned: {total_scanned}\n")
            f.write(f"Scan Started: {scan_start_time}\n")
            f.write("="*70 + "\n\n")
            
            # Devices found
            f.write(f"DEVICES FOUND: {len(found_devices)}\n")
            f.write("="*70 + "\n\n")
            
            for idx, device in enumerate(found_devices, 1):
                f.write(f"[{idx}] DEVICE: {device['ip']}\n")
                f.write("-"*70 + "\n")
                
                f.write(f"  IP Address:        {device['ip']}\n")
                f.write(f"  Device Name:       {device['hostname'] if device['hostname'] != 'Unknown' else 'Unknown'}\n")
                f.write(f"  NetBIOS Name:      {device['netbios'] if device['netbios'] != 'Unknown' else 'Not Available'}\n")
                f.write(f"  MAC Address:       {device['mac'] if device['mac'] != 'Unknown' else 'Not Available'}\n")
                f.write(f"  Manufacturer:      {device['manufacturer'] if device['manufacturer'] != 'Unknown' else 'Unknown'}\n")
                f.write(f"  Device Type:       {device['device_type']}\n")
                f.write(f"  User/Computer:     {device['user'] if device['user'] != 'Unknown' else 'Unknown'}\n")
                
                if device['ttl']:
                    f.write(f"  TTL:               {device['ttl']}\n")
                    f.write(f"  OS Guess:          {device['os_guess']}\n")
                
                f.write(f"  Status:            ONLINE\n\n")
                
                # Router detection
                if "Router" in device['device_type'] or "Gateway" in device['device_type']:
                    f.write(f"  >> WiFi ROUTER DETECTED <<\n\n")
                
                # Ports
                f.write(f"  OPEN PORTS & SERVICES:\n")
                for port_info in device['open_ports']:
                    port = port_info['port']
                    response_time = port_info['response_time']
                    service = "HTTP" if port == 80 else "HTTP-Alt/Proxy" if port == 8080 else "Unknown"
                    details = "Web Server (Unencrypted)" if port == 80 else "Alternative Web Server / Proxy"
                    
                    f.write(f"    - Port {port}/tcp - {service}\n")
                    f.write(f"      Service:         {service}\n")
                    f.write(f"      Details:         {details}\n")
                    f.write(f"      Response Time:   {response_time:.2f} ms\n")
                    port_str = '' if port == 80 else f':{port}'
                    f.write(f"      Access URL:      http://{device['ip']}{port_str}\n")
                
                f.write("\n" + "="*70 + "\n\n")
            
            # Summary table
            f.write("\nDEVICE SUMMARY TABLE\n")
            f.write("="*70 + "\n")
            f.write(f"{'IP Address':<16} {'Device Name':<25} {'Manufacturer':<15} {'Ports':<10}\n")
            f.write("-"*70 + "\n")
            
            for device in found_devices:
                ip = device['ip']
                name = device['hostname'] if device['hostname'] != "Unknown" else device['netbios']
                if name == "Unknown":
                    name = device['device_type']
                manufacturer = device['manufacturer'] if device['manufacturer'] != "Unknown" else "N/A"
                ports = ','.join([str(p['port']) for p in device['open_ports']])
                
                if len(name) > 24:
                    name = name[:21] + "..."
                if len(manufacturer) > 14:
                    manufacturer = manufacturer[:11] + "..."
                
                f.write(f"{ip:<16} {name:<25} {manufacturer:<15} {ports:<10}\n")
            
            # Router summary
            router_count = sum(1 for d in found_devices if "Router" in d['device_type'] or "Gateway" in d['device_type'])
            if router_count > 0:
                f.write("\n" + "="*70 + "\n")
                f.write(f"WIFI ROUTERS/GATEWAYS DETECTED: {router_count}\n")
                f.write("="*70 + "\n")
                for device in found_devices:
                    if "Router" in device['device_type'] or "Gateway" in device['device_type']:
                        router_name = device['hostname'] if device['hostname'] != "Unknown" else device['manufacturer']
                        f.write(f"  - {device['ip']:<16} {router_name}\n")
                        if device['mac'] != "Unknown":
                            f.write(f"    MAC: {device['mac']}\n")
                        if device['manufacturer'] != "Unknown":
                            f.write(f"    Manufacturer: {device['manufacturer']}\n")
            
            # Footer
            f.write("\n" + "="*70 + "\n")
            f.write("Scan completed: " + datetime.now().strftime('%B %d, %Y at %I:%M:%S %p') + "\n")
            f.write("Tool: W8IP-To Router v2.0\n")
            f.write("Developed by: W8Team / W8SOJIB\n")
            f.write("GitHub: github.com/W8SOJIB\n")
            f.write("="*70 + "\n")
        
        return filename
    except Exception as e:
        print(f"{Colors.RED}[!] Error saving to file: {e}{Colors.ENDC}")
        return None

def main():
    """
    Main function to run W8IP-To Router scanner (ULTRA FAST MODE)
    """
    # Clear screen and show banner
    clear_screen()
    print_banner()
    
    print(f"{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}          ULTRA FAST NETWORK SCANNER{Colors.ENDC}")
    print(f"{Colors.CYAN}       Scanning ports 80 and 8080 (HTTP/Web Services){Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.ENDC}\n")
    
    # Get IP range from user
    while True:
        start_ip = input(f"{Colors.YELLOW}[?] Enter start IP address: {Colors.ENDC}").strip()
        
        if not start_ip:
            print(f"{Colors.RED}[!] Please enter a valid IP address.{Colors.ENDC}")
            continue
            
        if validate_ip(start_ip):
            break
        else:
            print(f"{Colors.RED}[!] Invalid IP address format. Please try again.{Colors.ENDC}")
    
    while True:
        end_ip = input(f"{Colors.YELLOW}[?] Enter end IP address: {Colors.ENDC}").strip()
        
        if not end_ip:
            print(f"{Colors.RED}[!] Please enter a valid IP address.{Colors.ENDC}")
            continue
            
        if validate_ip(end_ip):
            break
        else:
            print(f"{Colors.RED}[!] Invalid IP address format. Please try again.{Colors.ENDC}")
    
    ip_list = generate_ip_range(start_ip, end_ip)
    print(f"\n{Colors.GREEN}[+] Generated {len(ip_list)} IP addresses to scan.{Colors.ENDC}")
    
    # Ports to scan
    ports_to_scan = [80, 8080]
    
    # Calculate optimal thread count (max 200 threads for ultra-fast scanning)
    max_workers = min(200, max(50, len(ip_list)))
    
    # Save scan start time
    scan_start_time = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}[*] Starting ULTRA FAST scan with {max_workers} threads...{Colors.ENDC}")
    print(f"{Colors.CYAN}[*] Time started: {scan_start_time}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    
    total_hosts_scanned = 0
    total_open_ports_found = 0
    hosts_with_open_ports = 0
    results_lock = threading.Lock()
    found_devices = []
    
    # Animation control
    animation_running = True
    animation_chars = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    
    def show_scanning_animation():
        """Display scanning animation while scan is running"""
        while animation_running:
            sys.stdout.write(f'\r{Colors.CYAN}[{next(animation_chars)}] Scanning IPs... Progress: {total_hosts_scanned}/{len(ip_list)} | Found: {hosts_with_open_ports} devices {Colors.ENDC}')
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\r' + ' ' * 80 + '\r')  # Clear the line
        sys.stdout.flush()
    
    # Start animation thread
    animation_thread = threading.Thread(target=show_scanning_animation, daemon=True)
    animation_thread.start()
    
    # Use ThreadPoolExecutor for concurrent scanning
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all scan jobs
        future_to_ip = {executor.submit(scan_single_ip, ip, ports_to_scan): ip for ip in ip_list}
        
        # Process results as they complete
        for future in as_completed(future_to_ip):
            total_hosts_scanned += 1
            result = future.result()
            
            # Only display results if open ports are found
            if result['open_ports']:
                with results_lock:
                    found_devices.append(result)
                    
                    # Temporarily stop animation to print device info
                    sys.stdout.write('\r' + ' ' * 100 + '\r')  # Clear animation line
                    sys.stdout.flush()
                    
                    print(f"\n{Colors.GREEN}{'='*70}{Colors.ENDC}")
                    print(f"{Colors.BOLD}{Colors.GREEN}[+] DEVICE FOUND: {result['ip']}{Colors.ENDC}")
                    print(f"{Colors.GREEN}{'='*70}{Colors.ENDC}")
                    
                    # Display device information
                    print(f"\n{Colors.CYAN}  DEVICE INFORMATION:{Colors.ENDC}")
                    print(f"{Colors.CYAN}  {'─'*66}{Colors.ENDC}")
                    
                    # Device Name / Hostname
                    device_name = result['hostname'] if result['hostname'] != "Unknown" else "Unknown"
                    print(f"  {Colors.BOLD}Device Name:{Colors.ENDC}       {Colors.YELLOW}{device_name}{Colors.ENDC}")
                    
                    # NetBIOS Name
                    netbios = result['netbios'] if result['netbios'] != "Unknown" else "Not Available"
                    print(f"  {Colors.BOLD}NetBIOS:{Colors.ENDC}           {Colors.YELLOW}{netbios}{Colors.ENDC}")
                    
                    # IP Address
                    print(f"  {Colors.BOLD}IP Address:{Colors.ENDC}        {Colors.CYAN}{result['ip']}{Colors.ENDC}")
                    
                    # MAC Address
                    mac = result['mac'] if result['mac'] != "Unknown" else "Not Available"
                    print(f"  {Colors.BOLD}MAC:{Colors.ENDC}                {Colors.YELLOW}{mac}{Colors.ENDC}")
                    
                    # Manufacturer
                    manufacturer = result['manufacturer'] if result['manufacturer'] != "Unknown" else "Unknown"
                    print(f"  {Colors.BOLD}Manufacturer:{Colors.ENDC}      {Colors.GREEN}{manufacturer}{Colors.ENDC}")
                    
                    # Device Type
                    print(f"  {Colors.BOLD}Type:{Colors.ENDC}               {Colors.BLUE}{result['device_type']}{Colors.ENDC}")
                    
                    # User/Computer Name
                    user = result['user'] if result['user'] != "Unknown" else "Unknown"
                    print(f"  {Colors.BOLD}User:{Colors.ENDC}               {Colors.YELLOW}{user}{Colors.ENDC}")
                    
                    # Advanced Info - TTL & OS
                    if result['ttl']:
                        print(f"  {Colors.BOLD}TTL:{Colors.ENDC}                {Colors.CYAN}{result['ttl']}{Colors.ENDC}")
                        print(f"  {Colors.BOLD}OS Guess:{Colors.ENDC}          {Colors.CYAN}{result['os_guess']}{Colors.ENDC}")
                    
                    # Status
                    print(f"  {Colors.BOLD}Status:{Colors.ENDC}             {Colors.GREEN}● ONLINE{Colors.ENDC}")
                    
                    # WiFi Router Detection
                    is_router = "Router" in result['device_type'] or "Gateway" in result['device_type']
                    if is_router:
                        router_name = result['hostname'] if result['hostname'] != "Unknown" else manufacturer
                        print(f"\n  {Colors.BOLD}{Colors.YELLOW}🔶 WiFi ROUTER DETECTED: {router_name}{Colors.ENDC}")
                    
                    # Display open ports with details
                    print(f"\n{Colors.CYAN}  OPEN PORTS & SERVICES:{Colors.ENDC}")
                    print(f"{Colors.CYAN}  {'─'*66}{Colors.ENDC}")
                    for port_info in result['open_ports']:
                        port = port_info['port']
                        response_time = port_info['response_time']
                        
                        # Determine service and details
                        if port == 80:
                            service = "HTTP"
                            details = "Web Server (Unencrypted)"
                        elif port == 8080:
                            service = "HTTP-Alt/Proxy"
                            details = "Alternative Web Server / Proxy"
                        else:
                            service = "Unknown"
                            details = "Unknown Service"
                        
                        print(f"  {Colors.GREEN}• Port {port}/tcp - {service}{Colors.ENDC}")
                        print(f"    {Colors.BOLD}Service:{Colors.ENDC}         {Colors.CYAN}{service}{Colors.ENDC}")
                        print(f"    {Colors.BOLD}Details:{Colors.ENDC}         {details}")
                        print(f"    {Colors.BOLD}Response Time:{Colors.ENDC}   {Colors.YELLOW}{response_time:.2f} ms{Colors.ENDC}")
                        
                        port_str = '' if port == 80 else f':{port}'
                        print(f"    {Colors.BOLD}Access URL:{Colors.ENDC}      {Colors.UNDERLINE}{Colors.BLUE}http://{result['ip']}{port_str}{Colors.ENDC}")
                        print()
                    
                    total_open_ports_found += len(result['open_ports'])
                    hosts_with_open_ports += 1
    
    # Stop animation
    animation_running = False
    time.sleep(0.2)  # Give animation thread time to stop
    
    # Display summary
    print(f"\n{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}SCAN COMPLETED - SUMMARY{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Total hosts scanned:{Colors.ENDC}      {Colors.YELLOW}{total_hosts_scanned}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Devices found (online):{Colors.ENDC}   {Colors.GREEN}{hosts_with_open_ports}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Total open ports found:{Colors.ENDC}   {Colors.GREEN}{total_open_ports_found}{Colors.ENDC}")
    print(f"{Colors.BOLD}  Scan completed:{Colors.ENDC}           {Colors.CYAN}{datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}{Colors.ENDC}")
    
    # List all found devices
    if found_devices:
        print(f"\n{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.YELLOW}ALL DISCOVERED DEVICES:{Colors.ENDC}")
        print(f"{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{'IP Address':<16} {'Device Name/Type':<25} {'Manufacturer':<15} {'Ports':<10}{Colors.ENDC}")
        print(f"{Colors.CYAN}{'-' * 70}{Colors.ENDC}")
        
        # Count routers
        router_count = 0
        
        for device in found_devices:
            ip = device['ip']
            name = device['hostname'] if device['hostname'] != "Unknown" else device['netbios']
            if name == "Unknown":
                name = device['device_type']
            
            manufacturer = device['manufacturer'] if device['manufacturer'] != "Unknown" else "N/A"
            ports = ','.join([str(p['port']) for p in device['open_ports']])
            device_type = device['device_type']
            
            # Mark routers with special symbol
            if "Router" in device_type or "Gateway" in device_type:
                router_count += 1
                name = f"🔶 {name}"
            
            # Truncate long names
            if len(name) > 24:
                name = name[:21] + "..."
            if len(manufacturer) > 14:
                manufacturer = manufacturer[:11] + "..."
            
            print(f"{Colors.CYAN}{ip:<16}{Colors.ENDC} {Colors.YELLOW}{name:<25}{Colors.ENDC} {Colors.GREEN}{manufacturer:<15}{Colors.ENDC} {Colors.BLUE}{ports:<10}{Colors.ENDC}")
        
        # WiFi Router Summary
        if router_count > 0:
            print(f"\n{Colors.YELLOW}{'=' * 70}{Colors.ENDC}")
            print(f"{Colors.BOLD}{Colors.YELLOW}🔶 WIFI ROUTERS/GATEWAYS DETECTED: {router_count}{Colors.ENDC}")
            print(f"{Colors.YELLOW}{'=' * 70}{Colors.ENDC}")
            for device in found_devices:
                if "Router" in device['device_type'] or "Gateway" in device['device_type']:
                    router_name = device['hostname'] if device['hostname'] != "Unknown" else device['manufacturer']
                    if router_name == "Unknown":
                        router_name = "Unknown Router"
                    print(f"{Colors.GREEN}  • {device['ip']:<16} - {Colors.BOLD}{router_name}{Colors.ENDC}")
                    if device['mac'] != "Unknown":
                        print(f"    {Colors.CYAN}MAC: {device['mac']}{Colors.ENDC}")
                    if device['manufacturer'] != "Unknown":
                        print(f"    {Colors.YELLOW}Manufacturer: {device['manufacturer']}{Colors.ENDC}")
    
    # Save results to file
    if found_devices:
        print(f"\n{Colors.YELLOW}[*] Saving results to file...{Colors.ENDC}")
        saved_file = save_results_to_file(found_devices, start_ip, end_ip, total_hosts_scanned, scan_start_time)
        if saved_file:
            print(f"{Colors.GREEN}[✓] Results saved to: {Colors.BOLD}{saved_file}{Colors.ENDC}")
        else:
            print(f"{Colors.RED}[!] Failed to save results to file{Colors.ENDC}")
    
    # Credits
    print(f"\n{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}[✓] Scan Complete!{Colors.ENDC}")
    print(f"{Colors.CYAN}{'─' * 70}{Colors.ENDC}")
    print(f"{Colors.YELLOW}Tool:{Colors.ENDC} {Colors.BOLD}W8IP-To Router{Colors.ENDC} v2.0")
    print(f"{Colors.YELLOW}Developed by:{Colors.ENDC} {Colors.BOLD}{Colors.GREEN}W8Team / W8SOJIB{Colors.ENDC}")
    print(f"{Colors.YELLOW}GitHub:{Colors.ENDC} {Colors.CYAN}github.com/W8SOJIB{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}[!] Scan interrupted by user.{Colors.ENDC}")
        print(f"{Colors.CYAN}{'─' * 70}{Colors.ENDC}")
        print(f"{Colors.GREEN}Tool: W8IP-To Router by W8Team / W8SOJIB{Colors.ENDC}")
        print(f"{Colors.CYAN}{'─' * 70}{Colors.ENDC}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}[!] An error occurred: {e}{Colors.ENDC}")
        sys.exit(1)

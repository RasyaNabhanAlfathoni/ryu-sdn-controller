# ryu-agent/utils/__init__.py
import os
import subprocess
import yaml
import glob

def detect_os_family():
    """Detect OS family - LEBIH DETAIL"""
    try:
        with open("/etc/os-release") as f:
            content = f.read().lower()
            
            # UBAH LOGIC JADI LEBIH SPECIFIC
            if 'ubuntu' in content:
                return 'ubuntu'
            elif 'debian' in content:
                return 'debian'
            elif 'centos' in content:
                return 'centos'      # CENTOS SPECIFIC
            elif 'rhel' in content or 'red hat' in content:
                return 'rhel'        # RED HAT ENTERPRISE
            elif 'fedora' in content:
                return 'fedora'
            elif 'suse' in content or 'opensuse' in content:
                return 'suse'
                
    except Exception:
        pass
    
    # FALLBACK DETECTION - LEBIH SPECIFIC
    try:
        if os.path.exists("/etc/centos-release"):
            with open("/etc/centos-release") as f:
                if 'centos' in f.read().lower():
                    return 'centos'
    except:
        pass
        
    try:
        if os.path.exists("/etc/redhat-release"):
            with open("/etc/redhat-release") as f:
                content = f.read().lower()
                if 'centos' in content:
                    return 'centos'
                elif 'red hat' in content:
                    return 'rhel'
                elif 'fedora' in content:
                    return 'fedora'
    except:
        pass
    
    if os.path.exists("/etc/debian_version"):
        return 'debian'
    
    return 'unknown'

def execute_command(cmd, timeout=30):
    """Execute command - Dipakai Semua Drivers"""
    try:
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timeout after {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# === NETWORK UTILITY FUNCTIONS ===

def detect_network_manager():
    """Detect active network configuration manager - HOST VERSION"""
    
    # Priority checks for HOST network manager
    checks = [
        # 1. Check Netplan on HOST
        ('netplan', lambda: _check_host_netplan()),
        
        # 2. Check NetworkManager/ifcfg on HOST  
        ('nm_ifcfg', lambda: _check_host_nm_ifcfg()),
        
        # 3. Check systemd-networkd on HOST
        ('systemd_networkd', lambda: _check_host_systemd_networkd()),
        
        # 4. Check Debian interfaces on HOST
        ('debian_interfaces', lambda: _check_host_debian_interfaces()),
        
        # 5. Fallback
        ('fallback', lambda: True)
    ]
    
    for name, check in checks:
        if check():
            return name
    return 'unknown'

def _check_host_netplan():
    """Check if host uses Netplan"""
    try:
        # Check if /etc/netplan exists on host
        result = execute_command("ls /etc/netplan/ 2>/dev/null | head -1")
        if result["success"] and result["stdout"]:
            return True
        
        # Check netplan binary on host
        result = execute_command("which netplan")
        return result["success"]
    except:
        return False

def _check_host_nm_ifcfg():
    """Check if host uses NetworkManager/ifcfg"""
    try:
        # Check ifcfg files on host
        result = execute_command("ls /etc/sysconfig/network-scripts/ifcfg-* 2>/dev/null | head -1")
        if result["success"] and result["stdout"]:
            return True
        
        # Check NetworkManager service on host
        result = execute_command("systemctl status NetworkManager 2>/dev/null | grep -q 'active (running)'")
        if result["success"]:
            return True
            
        # Check NetworkManager binary
        result = execute_command("which NetworkManager")
        return result["success"]
    except:
        return False

def _check_host_systemd_networkd():
    """Check if host uses systemd-networkd"""
    try:
        # Check systemd-networkd service on host
        result = execute_command("systemctl status systemd-networkd 2>/dev/null | grep -q 'active (running)'")
        if result["success"]:
            return True
            
        # Check networkd directory on host
        result = execute_command("ls /etc/systemd/network/ 2>/dev/null | head -1")
        return result["success"] and result["stdout"]
    except:
        return False

def _check_host_debian_interfaces():
    """Check if host uses Debian interfaces"""
    try:
        # Check if interfaces file exists and has content
        result = execute_command("[ -s /etc/network/interfaces ] && echo 'exists'")
        return result["success"] and result["stdout"] == "exists"
    except:
        return False


def cidr_to_netmask(cidr):
    """Convert CIDR to netmask"""
    try:
        cidr = int(cidr)
        mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
        return f"{(mask >> 24) & 0xff}.{(mask >> 16) & 0xff}.{(mask >> 8) & 0xff}.{mask & 0xff}"
    except:
        return "255.255.255.0"
    
def generate_uuid():
    """Generate UUID for network interfaces"""
    import uuid
    return str(uuid.uuid4())

def configure_network_interface(iface, ip_cidr, gateway=None, dns_servers=None, onboot=True, dhcp=False):
    """Complete network interface configuration"""
    try:
        network_manager = detect_network_manager()
        
        if network_manager == 'netplan':
            return configure_netplan(iface, ip_cidr, gateway, dns_servers, dhcp)
        elif network_manager == 'nm_ifcfg':
            return configure_ifcfg(iface, ip_cidr, gateway, dns_servers, onboot, dhcp)
        elif network_manager == 'systemd_networkd':
            return configure_systemd_networkd(iface, ip_cidr, gateway, dns_servers, dhcp)
        elif network_manager == 'debian_interfaces':
            return configure_debian_interfaces(iface, ip_cidr, gateway, dns_servers, dhcp)
        else:
            return {"status": "error", "error": f"Unsupported network manager: {network_manager}"}
            
    except Exception as e:
        return {"status": "error", "error": str(e)}

def configure_netplan(iface, ip_cidr, gateway=None, dns_servers=None, dhcp=False):
    """Complete Netplan configuration (Ubuntu)"""
    try:
        config_files = glob.glob('/etc/netplan/*.yaml')
        if not config_files:
            return {"status": "error", "error": "No netplan configuration files found"}
        
        config_file = config_files[0]
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f) or {}

        # Initialize structure
        if 'network' not in config:
            config['network'] = {'version': 2}
        if 'ethernets' not in config['network']:
            config['network']['ethernets'] = {}

        # Configure interface - DHCP atau STATIC
        if dhcp:
            # DHCP Configuration
            config['network']['ethernets'][iface] = {
                'dhcp4': True,
                'dhcp6': False  # Optional: disable IPv6 DHCP
            }
        else:
            # Static Configuration
            config['network']['ethernets'][iface] = {
                'dhcp4': False,
                'addresses': [ip_cidr] if ip_cidr else []
            }

        # Add gateway if provided
        if gateway:
            config['network']['ethernets'][iface]['gateway4'] = gateway

        # Add DNS if provided
        if dns_servers:
            config['network']['ethernets'][iface]['nameservers'] = {
                'addresses': dns_servers
            }

        # Write configuration
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        # Apply configuration
        apply_result = execute_command("netplan apply")
        
        return {
            "status": "success",
            "message": f"Complete network configuration applied for {iface}",
            "config_file": config_file,
            "dhcp": dhcp,
            "ip_address": ip_cidr if not dhcp else None,
            "gateway": gateway if not dhcp else None,
            "dns_servers": dns_servers if not dhcp else None,
            "applied": apply_result["success"]
        }

    except Exception as e:
        return {"status": "error", "error": f"netplan config failed: {str(e)}"}

def configure_ifcfg(iface, ip_cidr, gateway=None, dns_servers=None, onboot=True, dhcp=False):
    """Complete ifcfg configuration (RHEL/CentOS)"""
    try:
        ifcfg_file = f"/etc/sysconfig/network-scripts/ifcfg-{iface}"
        
        if dhcp:
            # DHCP Configuration
            config_lines = [
                f"TYPE=Ethernet\n",
                f"PROXY_METHOD=none\n",
                f"BROWSER_ONLY=no\n",
                f"BOOTPROTO=dhcp\n",  # DHCP mode
                f"DEFROUTE=yes\n",
                f"IPV4_FAILURE_FATAL=no\n",
                f"IPV6INIT=yes\n",
                f"IPV6_AUTOCONF=yes\n",
                f"IPV6_DEFROUTE=yes\n",
                f"IPV6_FAILURE_FATAL=no\n",
                f"IPV6_ADDR_GEN_MODE=stable-privacy\n",
                f"NAME={iface}\n",
                f"UUID={generate_uuid()}\n",
                f"DEVICE={iface}\n",
                f"ONBOOT={'yes' if onboot else 'no'}\n"
            ]
        else:
            # Static Configuration
            if '/' in ip_cidr:
                ip_address, prefix = ip_cidr.split('/')
            else:
                ip_address = ip_cidr
                prefix = "24"  # Default
            
            config_lines = [
                f"TYPE=Ethernet\n",
                f"PROXY_METHOD=none\n",
                f"BROWSER_ONLY=no\n",
                f"BOOTPROTO=none\n",  # Static mode
                f"DEFROUTE=yes\n",
                f"IPV4_FAILURE_FATAL=no\n",
                f"IPV6INIT=yes\n",
                f"IPV6_AUTOCONF=yes\n",
                f"IPV6_DEFROUTE=yes\n",
                f"IPV6_FAILURE_FATAL=no\n",
                f"IPV6_ADDR_GEN_MODE=stable-privacy\n",
                f"NAME={iface}\n",
                f"UUID={generate_uuid()}\n",
                f"DEVICE={iface}\n",
                f"ONBOOT={'yes' if onboot else 'no'}\n",
                f"IPADDR={ip_address}\n",
                f"PREFIX={prefix}\n"
            ]

        # Add gateway if provided
        if gateway:
            config_lines.append(f"GATEWAY={gateway}\n")

        # Add DNS servers if provided
        if dns_servers:
            for i, dns in enumerate(dns_servers, 1):
                config_lines.append(f"DNS{i}={dns}\n")

        # Write configuration
        with open(ifcfg_file, 'w') as f:
            f.writelines(config_lines)

        # Restart NetworkManager
        apply_result = execute_command("systemctl restart NetworkManager")
        
        return {
            "status": "success",
            "message": f"Complete ifcfg configuration applied for {iface}",
            "config_file": ifcfg_file,
            "dhcp": dhcp,
            "ip_address": ip_cidr if not dhcp else None,
            "prefix": prefix,
            "gateway": gateway if not dhcp else None,
            "dns_servers": dns_servers if not dhcp else None,
            "onboot": onboot,
            "applied": apply_result["success"]
        }

    except Exception as e:
        return {"status": "error", "error": f"ifcfg config failed: {str(e)}"}

def configure_systemd_networkd(iface, ip_cidr, gateway=None, dns_servers=None, dhcp=False):
    """Complete systemd-networkd configuration"""
    try:
        network_file = f"/etc/systemd/network/10-{iface}.network"
        
        if dhcp:
            # DHCP Configuration
            config_lines = [
                "[Match]\n",
                f"Name={iface}\n",
                "\n",
                "[Network]\n",
                "DHCP=yes\n"
            ]
        else:
            # Static Configuration
            config_lines = [
                "[Match]\n",
                f"Name={iface}\n",
                "\n",
                "[Network]\n",
                f"Address={ip_cidr}\n"
            ]

        # Add gateway if provided
        if gateway:
            config_lines.extend([
                "\n",
                "[Route]\n",
                f"Gateway={gateway}\n"
            ])

        # Add DNS if provided
        if dns_servers:
            dns_line = "DNS=" + " ".join(dns_servers) + "\n"
            config_lines.insert(4, dns_line)  # Insert after Address line

        # Write configuration
        with open(network_file, 'w') as f:
            f.writelines(config_lines)

        # Restart systemd-networkd
        apply_result = execute_command("systemctl restart systemd-networkd")
        
        return {
            "status": "success",
            "message": f"Complete systemd-networkd configuration applied for {iface}",
            "config_file": network_file,
            "dhcp": dhcp,
            "ip_address": ip_cidr if not dhcp else None,
            "gateway": gateway if not dhcp else None,
            "dns_servers": dns_servers if not dhcp else None,
            "applied": apply_result["success"]
        }

    except Exception as e:
        return {"status": "error", "error": f"systemd-networkd config failed: {str(e)}"}

def configure_debian_interfaces(iface, ip_cidr, gateway=None, dns_servers=None, dhcp=False):
    """Complete Debian interfaces configuration"""
    try:
        interfaces_file = "/etc/network/interfaces"
        
        # Parse IP and netmask from CIDR
        if '/' in ip_cidr:
            ip_address, prefix = ip_cidr.split('/')
            netmask = cidr_to_netmask(int(prefix))
        else:
            ip_address = ip_cidr
            netmask = "255.255.255.0"

        # Read existing content
        if os.path.exists(interfaces_file):
            with open(interfaces_file, 'r') as f:
                content = f.read()
        else:
            content = "# Network interfaces configuration\n"

        # Remove existing configuration for this interface
        lines = content.splitlines()
        new_lines = []
        skip_section = False
        
        for line in lines:
            if line.strip().startswith(f"auto {iface}") or line.strip().startswith(f"iface {iface} "):
                skip_section = True
                continue
            elif skip_section and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                skip_section = False
            
            if not skip_section:
                new_lines.append(line)

        # Add new complete configuration
        if dhcp:
            # DHCP Configuration
            new_config = f"""
# Configured by SDN Controller - DHCP
auto {iface}
iface {iface} inet dhcp
"""
        else:
            # Static Configuration
            if '/' in ip_cidr:
                ip_address, prefix = ip_cidr.split('/')
                netmask = cidr_to_netmask(int(prefix))
            else:
                ip_address = ip_cidr
                netmask = "255.255.255.0"

            new_config = f"""
# Configured by SDN Controller - Static
auto {iface}
iface {iface} inet static
    address {ip_address}
    netmask {netmask}
"""
            if gateway:
                new_config += f"    gateway {gateway}\n"
            
            if dns_servers:
                dns_servers_str = " ".join(dns_servers)
                new_config += f"    dns-nameservers {dns_servers_str}\n"

        new_config += "\n"
        
        # Combine content
        final_content = '\n'.join(new_lines) + new_config

        # Write configuration
        with open(interfaces_file, 'w') as f:
            f.write(final_content)

        # Restart networking
        apply_result = execute_command("systemctl restart networking")
        
        return {
            "status": "success",
            "message": f"Complete interfaces configuration applied for {iface}",
            "config_file": interfaces_file,
            "dhcp": dhcp,
            "ip_address": ip_cidr if not dhcp else None,
            "netmask": netmask if not dhcp else None,
            "gateway": gateway if not dhcp else None,
            "dns_servers": dns_servers if not dhcp else None,
            "applied": apply_result["success"]
        }

    except Exception as e:
        return {"status": "error", "error": f"interfaces config failed: {str(e)}"}


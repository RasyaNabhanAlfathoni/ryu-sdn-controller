# ryu-agent/utils/__init__.py
import os
import subprocess
import yaml
import glob
import ipaddress
import tempfile
import paramiko
from pathlib import Path

def setup_ssh_keys():
    """Automatically setup SSH keys for passwordless SSH to host"""
    try:  
        # Paths
        ssh_dir = "/root/.ssh"
        private_key_path = f"{ssh_dir}/ryu_agent"
        public_key_path = f"{private_key_path}.pub"
        authorized_keys_path = f"{ssh_dir}/authorized_keys"
        
        # Create .ssh directory if not exists
        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
        
        # Check if keys already exist
        if os.path.exists(private_key_path) and os.path.exists(public_key_path):
            print("DEBUG: SSH keys already exist")
            return True
        
        print("DEBUG: Generating new SSH key pair...")
        
        # Generate RSA key pair
        key = paramiko.RSAKey.generate(2048)
        
        # Save private key
        key.write_private_key_file(private_key_path)
        os.chmod(private_key_path, 0o600)
        print(f"DEBUG: Private key saved to {private_key_path}")
        
        # Save public key
        public_key = f"{key.get_name()} {key.get_base64()}"
        with open(public_key_path, 'w') as f:
            f.write(public_key)
        os.chmod(public_key_path, 0o644)
        print(f"DEBUG: Public key saved to {public_key_path}")
        
        # Get host's authorized_keys path (in chroot)
        host_authorized_keys = "/host-rootfs/root/.ssh/authorized_keys"
        
        # Create host's .ssh directory if not exists
        host_ssh_dir = "/host-rootfs/root/.ssh"
        if not os.path.exists(host_ssh_dir):
            os.makedirs(host_ssh_dir, mode=0o700, exist_ok=True)
        
        # Append public key to host's authorized_keys
        with open(host_authorized_keys, 'a+') as f:
            f.seek(0)
            content = f.read()
            if public_key not in content:
                f.write(f"\n{public_key}\n")
                print(f"DEBUG: Added public key to {host_authorized_keys}")
            else:
                print(f"DEBUG: Public key already in {host_authorized_keys}")
        
        # Fix permissions on host
        os.chmod(host_authorized_keys, 0o600)
        os.chmod(host_ssh_dir, 0o700)

        return True
        
    except Exception as e:
        print(f"DEBUG setup_ssh_keys: Exception: {str(e)}")
        return False

def execute_on_ssh(cmd, timeout=30, auto_setup=True):
    """Execute command on host on SSH with automatic key setup"""
    try:
        if auto_setup:
            # Try to setup SSH keys automatically
            setup_ssh_keys()
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        private_key_path = "/root/.ssh/ryu_agent"
        if not os.path.exists(private_key_path):
            private_key_path = "/host-rootfs/root/.ssh/ryu_agent"
        
        # Try key-based authentication first
        try:
            if os.path.exists(private_key_path):
                private_key = paramiko.RSAKey.from_private_key_file(private_key_path)
                ssh.connect(
                    hostname='127.0.0.1',
                    port=22,
                    username='root',
                    pkey=private_key,
                    timeout=timeout,
                    look_for_keys=False
                )
            else:
                ssh.connect(
                    hostname='127.0.0.1',
                    port=22,
                    username='root',
                    timeout=timeout,
                    look_for_keys=True
                )
                
        except Exception as auth_error:
            print(f"DEBUG: SSH auth failed: {auth_error}")
            
            # If SSH not working, fallback to execute_on_host for non-apply commands
            # For apply commands specifically, we need SSH
            if "apply" in cmd or "restart" in cmd or "systemctl" in cmd:
                return {"success": False, "error": f"SSH authentication failed: {auth_error}"}
            else:
                # For non-apply commands, use chroot
                return execute_on_host(cmd, timeout)
        
        print(f"DEBUG execute_on_ssh: Executing: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        
        exit_code = stdout.channel.recv_exit_status()
        stdout_str = stdout.read().decode().strip()
        stderr_str = stderr.read().decode().strip()
        
        ssh.close()
        
        return {
            "success": exit_code == 0,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "returncode": exit_code
        }
        
    except Exception as e:
        print(f"DEBUG execute_on_ssh: Exception: {str(e)}")
        return {"success": False, "error": str(e)}

def execute_on_host(cmd, timeout=30):
    """Execute command on HOST using chroot"""
    try:
        # Escape quotes dengan benar
        escaped_cmd = cmd.replace('"', '\\"').replace('$', '\\$')
        
        # Gunakan env vars untuk bypass D-Bus issues
        full_cmd = f"chroot /host-rootfs /bin/sh -c \"DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket {escaped_cmd}\""
        
        print(f"DEBUG execute_on_host: Running: {full_cmd}")
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        
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

def execute_command(cmd, timeout=30):
    """Execute command dalam container"""
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

def detect_os_family():
    """Detect OS family dari host"""
    try:
        result = execute_on_host("cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || echo ''")
        if result["success"] and result["stdout"]:
            content = result["stdout"].lower()
            
            if 'ubuntu' in content:
                return 'ubuntu'
            elif 'debian' in content:
                return 'debian'
            elif 'centos' in content:
                return 'centos'
            elif 'rhel' in content or 'red hat' in content:
                return 'rhel'
            elif 'fedora' in content:
                return 'fedora'
            elif 'suse' in content or 'opensuse' in content:
                return 'suse'
                
    except:
        pass
    
    return 'unknown'

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
        result = execute_on_host("find /etc/netplan -name '*.yaml' -type f 2>/dev/null | head -5")
        if result["success"] and result["stdout"]:
            return True
        
        result = execute_on_host("which netplan 2>/dev/null")
        return result["success"]
    except:
        return False

def _check_host_nm_ifcfg():
    """Check if host uses NetworkManager/ifcfg"""
    try:
        result = execute_on_host("ls /etc/sysconfig/network-scripts/ifcfg-* 2>/dev/null | head -1")
        if result["success"] and result["stdout"]:
            return True
        
        result = execute_on_host("systemctl status NetworkManager 2>/dev/null | grep -q 'active (running)'")
        if result["success"]:
            return True
            
        result = execute_on_host("which NetworkManager 2>/dev/null")
        return result["success"]
    except:
        return False

def _check_host_systemd_networkd():
    """Check if host uses systemd-networkd"""
    try:
        result = execute_on_host("systemctl status systemd-networkd 2>/dev/null | grep -q 'active (running)'")
        if result["success"]:
            return True
            
        result = execute_on_host("ls /etc/systemd/network/ 2>/dev/null | head -1")
        return result["success"] and result["stdout"]
    except:
        return False

def _check_host_debian_interfaces():
    """Check if host uses Debian interfaces"""
    try:
        result = execute_on_host("[ -s /etc/network/interfaces ] && echo 'exists'")
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

# === VALIDASI COMPACT ===

def validate_config(iface, ip_cidr=None, gateway=None, dns_servers=None, dhcp=False):
    """Compact validation before configuration"""
    errors = []
    warnings = []
    
    # 1. Check interface exists - dengan berbagai cara
    cmd = f"ip link show {iface} 2>/dev/null"
    print(f"DEBUG: Running command: {cmd}")
    result = execute_command(cmd)
    print(f"DEBUG: Command result: success={result['success']}, stdout={result['stdout'][:100]}, stderr={result['stderr']}")
    
    if not result["success"]:
        # Coba cara lain
        print(f"DEBUG: Trying alternative methods...")
        
        # Cek via sysfs
        cmd2 = f"ls /sys/class/net/"
        result2 = execute_command(cmd2)
        print(f"DEBUG: All interfaces: {result2['stdout']}")
        
        cmd3 = f"ls /sys/class/net/ | grep -w {iface}"
        result3 = execute_command(cmd3)
        print(f"DEBUG: grep result for {iface}: {result3['stdout']}")
        
        # Cek via ip addr
        cmd4 = "ip addr show"
        result4 = execute_command(cmd4)
        print(f"DEBUG: All ip addresses: {result4['stdout'][:200]}...")
        
        if not result3["success"] or iface not in result3["stdout"]:
            errors.append(f"Interface {iface} not found")
        else:
            print(f"DEBUG: Interface {iface} found via sysfs")
    else:
        print(f"DEBUG: Interface {iface} found via ip command")
    
    # 2. Validate for static IP
    if not dhcp:
        if not ip_cidr:
            errors.append("IP/CIDR required for static configuration")
        else:
            # Validate CIDR format
            try:
                network = ipaddress.IPv4Network(ip_cidr, strict=False)
                ip_address = ip_cidr.split('/')[0]
                
                # Skip IP conflict check untuk sekarang
                # Bisa menyebabkan false positive
                
            except (ValueError, ipaddress.AddressValueError):
                errors.append(f"Invalid CIDR format: {ip_cidr}")
    
    # 3. Validate gateway
    if gateway:
        try:
            ipaddress.IPv4Address(gateway)
        except (ValueError, ipaddress.AddressValueError):
            errors.append(f"Invalid gateway IP: {gateway}")
    
    # 4. Validate DNS
    if dns_servers:
        for dns in dns_servers:
            try:
                ipaddress.IPv4Address(dns)
            except (ValueError, ipaddress.AddressValueError):
                errors.append(f"Invalid DNS IP: {dns}")
                break
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "has_warnings": len(warnings) > 0
    }

def backup_if_exists(filepath):
    """Simple backup if file exists on HOST"""
    import shutil
    import time
    
    # Check if file exists on host
    result = execute_on_host(f"[ -f {filepath} ] && echo 'exists'")
    if not result["success"] or result["stdout"] != "exists":
        return None
    
    backup_dir = "/tmp/network_backups"
    
    # Create backup dir on host
    execute_on_host(f"mkdir -p {backup_dir}")
    
    timestamp = int(time.time())
    filename = os.path.basename(filepath)
    backup_file = f"{backup_dir}/{filename}_{timestamp}.bak"
    
    # Copy on host
    copy_result = execute_on_host(f"cp {filepath} {backup_file}")
    
    if copy_result["success"]:
        return backup_file
    else:
        return None

def configure_network_interface(iface, ip_cidr, gateway=None, dns_servers=None, onboot=True, dhcp=False):
    """Complete network interface configuration menggunakan nsenter"""
    # Validation Config
    validation = validate_config(iface, ip_cidr, gateway, dns_servers, dhcp)
    if not validation["valid"]:
        return {
            "status": "error",
            "error": "Validation failed",
            "details": validation["errors"]
        }

    network_manager = detect_network_manager()
    backup_path = None

    try:
        result = None

        if network_manager == 'netplan':
            result = configure_netplan(iface, ip_cidr, gateway, dns_servers, dhcp)
        elif network_manager == 'nm_ifcfg':
            result = configure_ifcfg(iface, ip_cidr, gateway, dns_servers, onboot, dhcp)
        elif network_manager == 'systemd_networkd':
            result = configure_systemd_networkd(iface, ip_cidr, gateway, dns_servers, dhcp)
        elif network_manager == 'debian_interfaces':
            result = configure_debian_interfaces(iface, ip_cidr, gateway, dns_servers, dhcp)
        else:
            result = {"status": "error", "error": f"Unsupported network manager: {network_manager}"}
        
        # Add validation info if successful
        if result and result.get("status") == "success":
            result["validation"] = validation
            if backup_path:
                result["backup"] = backup_path
            
        return result
        
    except Exception as e:
        return {"status": "error", "error": str(e)}
    
def apply_network_config_ssh(network_manager, config_file=None, iface=None):
    """Apply network configuration via SSH"""
    try:
        print(f"Network manager: {network_manager}, config_file: {config_file}")
        
        apply_commands = []
        
        if network_manager == 'netplan':
            # Apply netplan
            apply_commands.append("netplan apply")
            
        elif network_manager == 'nm_ifcfg':
            # Restart NetworkManager
            apply_commands.append("systemctl restart NetworkManager")
            
            # Jika ada interface spesifik, reload connection
            if iface:
                apply_commands.append(f"nmcli connection reload")
                apply_commands.append(f"nmcli connection down {iface} 2>/dev/null || true")
                apply_commands.append(f"nmcli connection up {iface} 2>/dev/null || true")
                
        elif network_manager == 'systemd_networkd':
            # Restart systemd-networkd
            apply_commands.append("systemctl restart systemd-networkd")
            
        elif network_manager == 'debian_interfaces':
            # Restart networking service
            apply_commands.append("systemctl restart networking || service networking restart")
            
        else:
            # Fallback: restart network service umum
            apply_commands.append("systemctl restart network || service network restart")
        
        # Execute all apply commands via SSH
        results = []
        for cmd in apply_commands:
            print(f"DEBUG: Applying via SSH: {cmd}")
            result = execute_on_ssh(cmd)
            results.append({
                "command": cmd,
                "success": result["success"],
                "output": result.get("stderr", result.get("stdout", ""))
            })
        
        # Check overall success
        success_count = sum(1 for r in results if r["success"])
        applied = success_count > 0
        
        return {
            "applied": applied,
            "results": results,
            "method": "ssh"
        }
        
    except Exception as e:
        print(f"DEBUG apply_network_config_ssh: Exception: {str(e)}")
        return {"applied": False, "error": str(e)}

def configure_netplan(iface, ip_cidr, gateway=None, dns_servers=None, dhcp=False):
    """Configure Netplan"""
    try:
        # Cari file config netplan
        result = execute_on_host("find /etc/netplan/*.yaml 2>/dev/null | head -1")
        if not result["success"]:
            return {"status": "error", "error": "No netplan configuration files found"}
        print(f"DEBUG configure_netplan: Looking for existing files: {result}")
        
        config_file = result["stdout"].strip()
        print(f"DEBUG configure_netplan: Using existing file: {config_file}")

        # Backup file asli
        backup_path = None
        check_result = execute_on_host(f"[ -f {config_file} ] && echo 'exists' || echo 'not found'")
        if check_result["success"] and check_result["stdout"] == "exists":
            print(f"DEBUG configure_netplan: File exists, creating backup")
            backup_path = backup_if_exists(config_file)
        
        # Baca content existing
        read_result = execute_on_host(f"cat {config_file} 2>/dev/null || echo ''")
        existing_content = read_result.get("stdout", "")
        
        if not existing_content:
            print("DEBUG: File empty or not found, creating new")
            existing_content = """network:
  version: 2
  ethernets: {}
"""
        
        # Parse YAML existing
        import yaml
        try:
            config = yaml.safe_load(existing_content)
            if not config:
                config = {"network": {"version": 2, "ethernets": {}}}
            elif "network" not in config:
                config = {"network": {"version": 2, "ethernets": {}}}
            elif "ethernets" not in config["network"]:
                config["network"]["ethernets"] = {}
        except yaml.YAMLError as e:
            print(f"DEBUG: Error parsing YAML: {e}, creating new config")
            config = {"network": {"version": 2, "ethernets": {}}}
        
        print(f"DEBUG: Existing config structure: {list(config['network']['ethernets'].keys())}")
        
        # Buat config untuk interface ini
        iface_config = {}
        
        if dhcp:
            iface_config = {
                "dhcp4": True,
                "dhcp6": False
            }
        else:
            iface_config = {
                "dhcp4": False,
                "addresses": [ip_cidr]
            }
            
            if gateway:
                iface_config["gateway4"] = gateway
            
            if dns_servers:
                iface_config["nameservers"] = {
                    "addresses": dns_servers
                }
        
        # Update hanya interface yang dimaksud
        config["network"]["ethernets"][iface] = iface_config
        
        print(f"DEBUG: Updated config for {iface}: {iface_config}")
        
        # Konversi ke YAML dengan format yang rapi
        yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False)
        
        print(f"DEBUG: New YAML content:\n{yaml_str}")
        
        # Tulis config baru ke host
        write_cmd = f"cat > {config_file} << 'EOF'\n{yaml_str}\nEOF"
        write_result = execute_on_host(write_cmd)
        
        if not write_result["success"]:
            return {"status": "error", "error": f"Failed to write config: {write_result.get('stderr')}"}
        
        # Apply netplan
        apply_result = apply_network_config_ssh('netplan', config_file, iface)
        
        # Verifikasi
        if not dhcp:
            ip_part = ip_cidr.split('/')[0]
            verify_cmd = f"ip -4 addr show {iface} 2>/dev/null | grep -o '{ip_part}/'"
            verify_result = execute_on_ssh(verify_cmd)
            ip_verified = verify_result["success"]
        else:
            ip_verified = True
        
        return {
            "status": "success",
            "message": f"Netplan configuration applied for {iface}",
            "config_file": config_file,
            "dhcp": dhcp,
            "ip_address": ip_cidr if not dhcp else None,
            "gateway": gateway if not dhcp else None,
            "dns_servers": dns_servers if not dhcp else None,
            "applied": apply_result.get("applied", False),
            "ip_verified": ip_verified,
            "backup": backup_path,
            "apply_output": str(apply_result)
        }
        
    except Exception as e:
        # Cetak traceback untuk mengetahui error 
        import traceback
        error_trace = traceback.format_exc()
        print(f"DEBUG configure_netplan exception: {error_trace}")
        
        return {
            "status": "error", 
            "error": f"netplan config failed: {type(e).__name__}: {str(e)}"
        }

def configure_ifcfg(iface, ip_cidr, gateway=None, dns_servers=None, onboot=True, dhcp=False):
    """Configure ifcfg menggunakan nsenter"""
    try:
        config_file = f"/etc/sysconfig/network-scripts/ifcfg-{iface}"
        
        if dhcp:
            config_lines = [
                f"TYPE=Ethernet",
                f"PROXY_METHOD=none",
                f"BROWSER_ONLY=no",
                f"BOOTPROTO=dhcp",
                f"DEFROUTE=yes",
                f"IPV4_FAILURE_FATAL=no",
                f"IPV6INIT=yes",
                f"IPV6_AUTOCONF=yes",
                f"IPV6_DEFROUTE=yes",
                f"IPV6_FAILURE_FATAL=no",
                f"IPV6_ADDR_GEN_MODE=stable-privacy",
                f"NAME={iface}",
                f"UUID={generate_uuid()}",
                f"DEVICE={iface}",
                f"ONBOOT={'yes' if onboot else 'no'}"
            ]
        else:
            if '/' in ip_cidr:
                ip_address, prefix = ip_cidr.split('/')
            else:
                ip_address = ip_cidr
                prefix = "24"
            
            config_lines = [
                f"TYPE=Ethernet",
                f"PROXY_METHOD=none",
                f"BROWSER_ONLY=no",
                f"BOOTPROTO=none",
                f"DEFROUTE=yes",
                f"IPV4_FAILURE_FATAL=no",
                f"IPV6INIT=yes",
                f"IPV6_AUTOCONF=yes",
                f"IPV6_DEFROUTE=yes",
                f"IPV6_FAILURE_FATAL=no",
                f"IPV6_ADDR_GEN_MODE=stable-privacy",
                f"NAME={iface}",
                f"UUID={generate_uuid()}",
                f"DEVICE={iface}",
                f"ONBOOT={'yes' if onboot else 'no'}",
                f"IPADDR={ip_address}",
                f"PREFIX={prefix}"
            ]
            
            if gateway:
                config_lines.append(f"GATEWAY={gateway}")
            
            if dns_servers:
                for i, dns in enumerate(dns_servers, 1):
                    config_lines.append(f"DNS{i}={dns}")
        
        # Backup
        backup_path = backup_if_exists(config_file)
        
        # Write config ke host
        config_content = '\n'.join(config_lines)
        write_cmd = f"cat > {config_file} << 'EOF'\n{config_content}\nEOF"
        write_result = execute_on_host(write_cmd)
        
        if not write_result["success"]:
            return {"status": "error", "error": f"Failed to write config: {write_result.get('stderr')}"}
        
        # Restart NetworkManager
        apply_result = apply_network_config_ssh('nm_ifcfg', config_file, iface)
        
        return {
            "status": "success",
            "message": f"ifcfg configuration applied for {iface}",
            "config_file": config_file,
            "dhcp": dhcp,
            "ip_address": ip_cidr if not dhcp else None,
            "gateway": gateway if not dhcp else None,
            "dns_servers": dns_servers if not dhcp else None,
            "onboot": onboot,
            "applied": apply_result["success"],
            "backup": backup_path,
            "apply_output": apply_result.get("stderr", "")
        }
        
    except Exception as e:
        return {"status": "error", "error": f"ifcfg config failed: {str(e)}"}

def configure_systemd_networkd(iface, ip_cidr, gateway=None, dns_servers=None, dhcp=False):
    """Configure systemd-networkd menggunakan nsenter"""
    try:
        config_file = f"/etc/systemd/network/10-{iface}.network"
        
        if dhcp:
            config_content = f"""[Match]
Name={iface}

[Network]
DHCP=yes
"""
        else:
            config_content = f"""[Match]
Name={iface}

[Network]
Address={ip_cidr}
"""
            
            if dns_servers:
                dns_line = "DNS=" + " ".join(dns_servers)
                config_content += f"{dns_line}\n"
            
            if gateway:
                config_content += f"""
[Route]
Gateway={gateway}
"""
        
        # Backup
        backup_path = backup_if_exists(config_file)
        
        # Write config ke host
        write_cmd = f"cat > {config_file} << 'EOF'\n{config_content}\nEOF"
        write_result = execute_on_host(write_cmd)
        
        if not write_result["success"]:
            return {"status": "error", "error": f"Failed to write config: {write_result.get('stderr')}"}
        
        # Restart systemd-networkd
        apply_result = apply_network_config_ssh('systemd-networkd', config_file, iface)
        
        return {
            "status": "success",
            "message": f"systemd-networkd configuration applied for {iface}",
            "config_file": config_file,
            "dhcp": dhcp,
            "ip_address": ip_cidr if not dhcp else None,
            "gateway": gateway if not dhcp else None,
            "dns_servers": dns_servers if not dhcp else None,
            "applied": apply_result["success"],
            "backup": backup_path,
            "apply_output": apply_result.get("stderr", "")
        }
        
    except Exception as e:
        return {"status": "error", "error": f"systemd-networkd config failed: {str(e)}"}

def configure_debian_interfaces(iface, ip_cidr, gateway=None, dns_servers=None, dhcp=False):
    """Configure Debian interfaces menggunakan nsenter"""
    try:
        config_file = "/etc/network/interfaces"
        
        # Parse IP
        if '/' in ip_cidr:
            ip_address, prefix = ip_cidr.split('/')
            netmask = cidr_to_netmask(int(prefix))
        else:
            ip_address = ip_cidr
            netmask = "255.255.255.0"
        
        if dhcp:
            config_content = f"""
# Configured by SDN Controller - DHCP
auto {iface}
iface {iface} inet dhcp
"""
        else:
            config_content = f"""
# Configured by SDN Controller - Static
auto {iface}
iface {iface} inet static
    address {ip_address}
    netmask {netmask}
"""
            
            if gateway:
                config_content += f"    gateway {gateway}\n"
            
            if dns_servers:
                dns_servers_str = " ".join(dns_servers)
                config_content += f"    dns-nameservers {dns_servers_str}\n"
        
        # Backup
        backup_path = backup_if_exists(config_file)
        
        # Baca content existing
        read_result = execute_on_host(f"cat {config_file} 2>/dev/null || echo ''")
        existing_content = read_result.get("stdout", "")
        
        # Remove existing config untuk interface ini
        lines = existing_content.splitlines()
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
        
        # Gabung dengan config baru
        final_content = '\n'.join(new_lines) + config_content
        
        # Write ke host
        write_cmd = f"cat > {config_file} << 'EOF'\n{final_content}\nEOF"
        write_result = execute_on_host(write_cmd)
        
        if not write_result["success"]:
            return {"status": "error", "error": f"Failed to write config: {write_result.get('stderr')}"}
        
        chmod_cmd = f"chmod 600 {config_file}"
        execute_on_host(chmod_cmd)
        
        # Restart networking
        apply_result = apply_network_config_ssh('debian_interfaces', config_file, iface)
        
        return {
            "status": "success",
            "message": f"Debian interfaces configuration applied for {iface}",
            "config_file": config_file,
            "dhcp": dhcp,
            "ip_address": ip_cidr if not dhcp else None,
            "gateway": gateway if not dhcp else None,
            "dns_servers": dns_servers if not dhcp else None,
            "applied": apply_result["success"],
            "backup": backup_path,
            "apply_output": apply_result.get("stderr", "")
        }
        
    except Exception as e:
        return {"status": "error", "error": f"interfaces config failed: {str(e)}"}
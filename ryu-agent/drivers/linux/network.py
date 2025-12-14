import os
import subprocess
import re
import psutil
from utils import detect_os_family, execute_command, detect_network_manager, configure_network_interface

class ServerNetworkDriver:
    def __init__(self, logger=print):
        self.logger = logger
        self.os_family = detect_os_family()
        self._execute_command = execute_command
        self.network_manager = detect_network_manager()
        self.logger(f"Detected OS: {self.os_family}, Network Manager: {self.network_manager}")

    # === Network Monitoring ===
    def get_ip_info(self, iface):
        """Get IP and MAC address information"""
        try:
            # Method 1: Use psutil (primary)
            addrs = psutil.net_if_addrs().get(iface, [])
            ip_addresses = []
            mac_address = "unknown"
            
            for addr in addrs:
                if addr.family == 2:  # AF_INET - IPv4
                    ip_addresses.append(f"{addr.address}/{addr.netmask}")
                elif addr.family == 10:  # AF_INET6 - IPv6
                    # Skip IPv6 for simplicity, or include if needed
                    pass
                elif addr.family == 17:  # AF_LINK - MAC
                    mac_address = addr.address
            
            # Method 2: Fallback to ip command
            if not ip_addresses:
                result = self._execute_command(f"ip addr show {iface}")
                if result["success"]:
                    ip_match = re.findall(r'inet (\d+\.\d+\.\d+\.\d+/\d+)', result["stdout"])
                    ip_addresses = ip_match
                    
                    mac_match = re.search(r'link/ether ([\da-f:]+)', result["stdout"])
                    if mac_match and mac_address == "unknown":
                        mac_address = mac_match.group(1)

            interface_status = self.get_interface_status(iface)

            return {
                "interface": iface,
                "ip_addresses": ip_addresses,
                "mac_address": mac_address,
                "status": interface_status 
            }
        except Exception as e:
            return {"interface": iface, "error": str(e)}
        
    def get_interface_status(self, iface):
        """Helper untuk mendapatkan status interface (up/down)"""
        try:
            # Method 1: Check via sysfs
            operstate_path = f"/sys/class/net/{iface}/operstate"
            if os.path.exists(operstate_path):
                with open(operstate_path, 'r') as f:
                    status = f.read().strip().lower()
                    if status == 'up':
                        return 'up'
                    elif status == 'down':
                        return 'down'
            
            # Method 2: Check via ip command
            result = self._execute_command(f"ip link show {iface}")
            if result["success"]:
                output = result["stdout"].lower()
                if 'state up' in output or '<up>' in output:
                    return 'up'
                elif 'state down' in output or '<down>' in output:
                    return 'down'
            
            return 'unknown'
        except Exception as e:
            self.logger(f"Error getting interface status for {iface}: {e}")
            return 'unknown'

    def get_routing_table(self):
        """Get routing table"""
        try:
            result = self._execute_command("ip route show")
            if result["success"]:
                return result["stdout"].splitlines()
            else:
                return {"error": result.get("error", result["stderr"])}
        except Exception as e:
            self.logger(f"Error getting routing table: {e}")
            return {"error": str(e)}
        
    def get_dns_config(self):
        """Get current DNS configuration"""
        try:
            if os.path.exists("/etc/resolv.conf"):
                with open("/etc/resolv.conf", 'r') as f:
                    content = f.read()
                
                # Parse nameservers
                nameservers = []
                for line in content.splitlines():
                    if line.startswith('nameserver'):
                        nameservers.append(line.split()[1])
                
                return {
                    "status": "success",
                    "nameservers": nameservers,
                    "resolv_conf": content
                }
            else:
                return {"status": "error", "error": "/etc/resolv.conf not found"}
                
        except Exception as e:
            self.logger(f"Error getting DNS config: {e}")
            return {"status": "error", "error": str(e)}

    def port_scan(self, target, ports=None):
        """Port scanning - check if nmap is available"""
        try:
            # Check if nmap is installed
            check_result = self._execute_command("which nmap")
            if not check_result["success"]:
                return {"error": "nmap is not installed. Install with: sudo apt-get install nmap (Ubuntu) or sudo yum install nmap (RHEL)"}
            
            if ports:
                cmd = f"nmap -p {ports} {target}"
            else:
                cmd = f"nmap {target}"
            
            result = self._execute_command(cmd)
            if result["success"]:
                return result["stdout"]
            else:
                return {"error": result.get("error", result["stderr"])}
        except Exception as e:
            self.logger(f"Error in port scan: {e}")
            return {"error": str(e)}

    # === Network Controlling ===
    def configure_interface(self, iface, ip_cidr, gateway=None, dns_servers=None, onboot=True, dhcp=False):
        """Interface configuration with ip, gateway, DNS, etc."""
        try:
            # Ambil fungsi configure_network_interface dari utils/__init__.py
            result = configure_network_interface(iface, ip_cidr, gateway, dns_servers, onboot, dhcp)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def add_ip(self, iface, ip_cidr):
        """Add IP address to interface"""
        result = self._execute_command(f"ip addr add {ip_cidr} dev {iface}")
        return result["stdout"] if result["success"] else f"Error: {result.get('error', result['stderr'])}"

    def del_ip(self, iface, ip_cidr):
        """Remove IP address from interface"""
        result = self._execute_command(f"ip addr del {ip_cidr} dev {iface}")
        return result["stdout"] if result["success"] else f"Error: {result.get('error', result['stderr'])}"

    def enable_iface(self, iface):
        """Enable network interface"""
        result = self._execute_command(f"ip link set {iface} up")
        return result["stdout"] if result["success"] else f"Error: {result.get('error', result['stderr'])}"

    def disable_iface(self, iface):
        """Disable network interface"""
        result = self._execute_command(f"ip link set {iface} down")
        return result["stdout"] if result["success"] else f"Error: {result.get('error', result['stderr'])}"
    
    def add_route(self, network, gateway=None, interface=None):
        """Add static route"""
        try:
            if gateway and interface:
                cmd = f"ip route add {network} via {gateway} dev {interface}"
            elif gateway:
                cmd = f"ip route add {network} via {gateway}"
            elif interface:
                cmd = f"ip route add {network} dev {interface}"
            else:
                return {"error": "Either gateway or interface must be specified"}
            
            result = self._execute_command(cmd)
            if result["success"]:
                return {
                    "status": "success", 
                    "message": f"Route added: {network}",
                    "command": cmd
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("error", result["stderr"])
                }
        except Exception as e:
            self.logger(f"Error adding route: {e}")
            return {"status": "error", "error": str(e)}

    def delete_route(self, network, gateway=None, interface=None):
        """Delete static route"""
        try:
            if gateway and interface:
                cmd = f"ip route del {network} via {gateway} dev {interface}"
            elif gateway:
                cmd = f"ip route del {network} via {gateway}"
            elif interface:
                cmd = f"ip route del {network} dev {interface}"
            else:
                cmd = f"ip route del {network}"
            
            result = self._execute_command(cmd)
            if result["success"]:
                return {
                    "status": "success", 
                    "message": f"Route deleted: {network}",
                    "command": cmd
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("error", result["stderr"])
                }
        except Exception as e:
            self.logger(f"Error deleting route: {e}")
            return {"status": "error", "error": str(e)}
        
    def set_dns_servers(self, dns_servers):
        """Configure DNS servers"""
        try:
            if not isinstance(dns_servers, list):
                return {"status": "error", "error": "dns_servers must be a list"}
            
            # Backup current resolv.conf
            backup_result = self._execute_command("cp /etc/resolv.conf /etc/resolv.conf.backup")
            
            # Create new resolv.conf
            resolv_content = "# Generated by Agent API\n"
            for dns in dns_servers:
                resolv_content += f"nameserver {dns}\n"
            
            # Write to temporary file first
            temp_file = "/tmp/resolv.conf.tmp"
            with open(temp_file, 'w') as f:
                f.write(resolv_content)
            
            # Move to actual location with sudo
            result = self._execute_command(f"mv {temp_file} /etc/resolv.conf")
            
            if result["success"]:
                return {
                    "status": "success",
                    "message": f"DNS servers updated: {dns_servers}",
                    "backup_created": backup_result["success"]
                }
            else:
                # Restore backup if failed
                if backup_result["success"]:
                    self._execute_command("cp /etc/resolv.conf.backup /etc/resolv.conf")
                return {
                    "status": "error",
                    "error": result.get("error", result["stderr"])
                }
                
        except Exception as e:
            self.logger(f"Error setting DNS: {e}")
            return {"status": "error", "error": str(e)}
    
    def restart_network(self):
        """Restart network service"""
        try:
            # Try different service names
            services = ['network', 'networking', 'systemctl restart NetworkManager']
            
            for service in services:
                result = self._execute_command(f"systemctl restart {service}")
                if result["success"]:
                    return {
                        "status": "success",
                        "message": f"Network service restarted: {service}",
                        "service_used": service
                    }
            
            return {
                "status": "error",
                "error": "Failed to restart network service with any known service name"
            }
        except Exception as e:
            self.logger(f"Error restarting network: {e}")
            return {"status": "error", "error": str(e)}
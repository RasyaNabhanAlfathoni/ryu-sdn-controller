import os
import subprocess
import re
import psutil
import ipaddress
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
            # Use psutil (primary)
            addrs = psutil.net_if_addrs().get(iface, [])
            ip_addresses = []
            mac_address = "unknown"
            
            for addr in addrs:
                if addr.family == 2:  # AF_INET - IPv4
                    ip_info = {
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "cidr": self._netmask_to_cidr(addr.netmask),
                        "network": "",
                        "broadcast": ""
                    }
                    try:
                        if addr.address and addr.netmask:
                            network_obj = ipaddress.IPv4Network(f"{addr.address}/{addr.netmask}", strict=False)
                            ip_info["network"] = str(network_obj.network_address)
                            ip_info["broadcast"] = str(network_obj.broadcast_address)
                    except Exception as e:
                        self.logger(f"Error calculating network/broadcast: {e}")
                
                    ip_addresses.append(ip_info)
                elif addr.family == 10:  # AF_INET6 - IPv6
                    # Skip IPv6 for simplicity, or include if needed
                    pass
                elif addr.family == 17:  # AF_LINK - MAC
                    mac_address = addr.address
            
            # Method 2: Fallback to ip command
            if not ip_addresses:
                result = self._execute_command(f"ip addr show {iface}")
                if result["success"]:
                    ip_addresses = self._parse_ip_addr_output(result["stdout"], iface)
                    
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
        
    def _netmask_to_cidr(self, netmask):
        """Convert netmask to CIDR notation"""
        try:
            if not netmask:
                return ""
            
            # If already in CIDR format (e.g., "24")
            if isinstance(netmask, str) and netmask.isdigit():
                return int(netmask)
            
            # Convert dotted decimal to CIDR
            return sum(bin(int(x)).count('1') for x in netmask.split('.'))
        except Exception as e:
            self.logger(f"Error converting netmask to CIDR: {e}")
            return ""
    
    def _parse_ip_addr_output(self, output, iface):
        """Parse ip addr command output"""
        ip_addresses = []
        
        # Regex untuk IPv4 dengan netmask
        ipv4_pattern = r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)'
        matches = re.findall(ipv4_pattern, output)
        
        for address, prefix in matches:
            ip_info = {
                "address": address,
                "cidr": int(prefix),
                "network": "",
                "broadcast": "",
                "netmask": ""
            }
            
            # Calculate network and broadcast
            try:
                network_obj = ipaddress.IPv4Network(f"{address}/{prefix}", strict=False)
                ip_info["network"] = str(network_obj.network_address)
                ip_info["broadcast"] = str(network_obj.broadcast_address)
                ip_info["netmask"] = str(network_obj.netmask)
            except Exception as e:
                self.logger(f"Error parsing network for {address}/{prefix}: {e}")
            
            ip_addresses.append(ip_info)
        
        return ip_addresses
        
    def list_interfaces(self):
        """List all network interfaces"""
        try:
            interfaces = []
            
            # Method 1: Use psutil
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()
            
            for iface in net_if_addrs.keys():
                stats = net_if_stats.get(iface)
                addrs = net_if_addrs.get(iface, [])
                
                # Find MAC address
                mac_address = "unknown"
                for addr in addrs:
                    if addr.family == 17:  # AF_LINK - MAC
                        mac_address = addr.address
                        break
                
                # Find IPv4 addresses
                ipv4_addresses = []
                for addr in addrs:
                    if addr.family == 2:  # AF_INET - IPv4
                        ipv4_addresses.append(f"{addr.address}/{self._netmask_to_cidr(addr.netmask)}")
                
                # Get interface status
                status = "down"
                if stats and stats.isup:
                    status = "up"
                
                interfaces.append({
                    "name": iface,
                    "mac_address": mac_address,
                    "status": status,
                    "mtu": stats.mtu if stats else 1500,
                    "ipv4_addresses": ipv4_addresses,
                    "ipv4_count": len(ipv4_addresses)
                })
            
            # Method 2: Fallback to ip command
            if not interfaces:
                result = self._execute_command("ip link show")
                if result["success"]:
                    interfaces = self._parse_ip_link_output(result["stdout"])
            
            return {
                "success": True,
                "interfaces": interfaces,
                "total_interfaces": len(interfaces)
            }
            
        except Exception as e:
            self.logger(f"Error listing interfaces: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_ip_link_output(self, output):
        """Parse ip link command output"""
        interfaces = []
        current_iface = None
        
        for line in output.splitlines():
            if_match = re.match(r'^\d+: (\w+):\s+<(.+?)>', line)
            if if_match:
                current_iface = if_match.group(1)
                flags = if_match.group(2).split(',')
                
                # Get MTU
                mtu_match = re.search(r'mtu (\d+)', line)
                mtu = int(mtu_match.group(1)) if mtu_match else 1500
                
                # Get status
                status = "down"
                if "UP" in flags:
                    status = "up"
                
                # Get MAC address from next line
                mac_address = "unknown"
                
                interfaces.append({
                    "name": current_iface,
                    "mac_address": mac_address,  # Will be updated below
                    "status": status,
                    "mtu": mtu,
                    "ipv4_addresses": [],
                    "ipv4_count": 0
                })
            
            # MAC address line: link/ether 00:0c:29:xx:xx:xx brd ff:ff:ff:ff:ff:ff
            elif current_iface and 'link/ether' in line:
                mac_match = re.search(r'link/ether ([\da-f:]+)', line)
                if mac_match:
                    # Update MAC address for current interface
                    for iface in interfaces:
                        if iface["name"] == current_iface:
                            iface["mac_address"] = mac_match.group(1)
                            break
        
        # Now get IP addresses for each interface
        for iface in interfaces:
            ip_result = self._execute_command(f"ip -4 addr show {iface['name']}")
            if ip_result["success"]:
                ip_matches = re.findall(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)', ip_result["stdout"])
                iface["ipv4_addresses"] = [f"{ip}/{prefix}" for ip, prefix in ip_matches]
                iface["ipv4_count"] = len(ip_matches)
        
        return interfaces

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
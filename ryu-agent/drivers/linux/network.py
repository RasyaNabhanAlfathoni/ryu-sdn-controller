import os
import subprocess
import re
import psutil
from utils import detect_os_family, execute_command

class ServerNetworkDriver:
    def __init__(self, logger=print):
        self.logger = logger
        self.os_family = detect_os_family()
        self._execute_command = execute_command
        self.logger(f"Detected OS: {self.os_family}")

    # === Network Monitoring ===
    def list_interfaces(self):
        """Get list of network interfaces"""
        try:
            # Method 1: Use psutil (cross-platform)
            interfaces = list(psutil.net_if_addrs().keys())
            
            # Method 2: Use sysfs (Linux specific)
            if os.path.exists("/sys/class/net/"):
                sysfs_interfaces = os.listdir("/sys/class/net/")
                interfaces = list(set(interfaces + sysfs_interfaces))
            
            # Filter out loopback and virtual interfaces
            filtered = [iface for iface in interfaces 
                       if iface != "lo" and not iface.startswith(('virbr', 'docker', 'veth', 'br-'))]
            
            return filtered
        except Exception as e:
            self.logger(f"Error listing interfaces: {e}")
            return []

    def get_interface_details(self):
        """Get detailed interface information"""
        interfaces = self.list_interfaces()
        result = []
        
        for iface in interfaces:
            try:
                info = self.get_ip_info(iface)
                
                # Get interface status
                status = self.get_interface_status(iface)
                info["status"] = status
                
                # Get additional info from psutil
                if_addrs = psutil.net_if_addrs().get(iface, [])
                stats = psutil.net_if_stats().get(iface)
                
                if stats:
                    info["is_up"] = stats.isup
                    info["speed"] = stats.speed
                    info["mtu"] = stats.mtu
                
                result.append(info)
            except Exception as e:
                result.append({"interface": iface, "error": str(e)})
        
        return result

    def get_interface_status(self, iface):
        """Get interface status using multiple methods"""
        try:
            # Method 1: Use psutil
            stats = psutil.net_if_stats().get(iface)
            if stats:
                return 'up' if stats.isup else 'down'
            
            # Method 2: Use ip command
            result = self._execute_command(f"ip link show {iface}")
            if result["success"]:
                if 'state UP' in result["stdout"]:
                    return 'up'
                elif 'state DOWN' in result["stdout"]:
                    return 'down'
            
            # Method 3: Check sysfs
            operstate_path = f"/sys/class/net/{iface}/operstate"
            if os.path.exists(operstate_path):
                with open(operstate_path, 'r') as f:
                    return f.read().strip()
                    
            return 'unknown'
        except Exception as e:
            self.logger(f"Error getting status for {iface}: {e}")
            return 'unknown'

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

            return {
                "interface": iface,
                "ip_addresses": ip_addresses,
                "mac_address": mac_address
            }
        except Exception as e:
            return {"interface": iface, "error": str(e)}

    def show_all(self):
        """Show all interfaces with IP info"""
        all_ifaces = self.list_interfaces()
        return [self.get_ip_info(i) for i in all_ifaces]

    def get_interface_ips(self, iface):
        """Get IP addresses for specific interface"""
        info = self.get_ip_info(iface)
        return info.get("ip_addresses", [])

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

    def get_arp_table(self):
        """Get ARP table"""
        try:
            result = self._execute_command("ip neighbor show")
            if result["success"]:
                return result["stdout"].splitlines()
            else:
                return {"error": result.get("error", result["stderr"])}
        except Exception as e:
            self.logger(f"Error getting ARP table: {e}")
            return {"error": str(e)}

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

    def get_network_connections(self):
        """Get network connections"""
        try:
            # Use ss command (modern replacement for netstat)
            result = self._execute_command("ss -tunlp")
            if result["success"]:
                connections = []
                for line in result["stdout"].splitlines()[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 6 and 'LISTEN' in line:
                        conn_info = {
                            "protocol": "tcp",
                            "local_address": parts[4],
                            "process": parts[-1] if "users:(" in parts[-1] else ""
                        }
                        connections.append(conn_info)
                return connections
            else:
                return {"error": result.get("error", result["stderr"])}
        except Exception as e:
            self.logger(f"Error getting network connections: {e}")
            return {"error": str(e)}

    def get_interface_counters(self, iface):
        """Get interface statistics"""
        try:
            # Method 1: Use psutil
            counters = psutil.net_io_counters(pernic=True).get(iface)
            if counters:
                return {
                    "interface": iface,
                    "rx_bytes": counters.bytes_recv,
                    "rx_packets": counters.packets_recv,
                    "tx_bytes": counters.bytes_sent,
                    "tx_packets": counters.packets_sent,
                    "rx_errors": counters.errin,
                    "tx_errors": counters.errout
                }
            
            # Method 2: Fallback to /proc/net/dev
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()
            
            for line in lines[2:]:  # Skip headers
                parts = line.split()
                if parts[0].strip(':') == iface:
                    return {
                        "interface": iface,
                        "rx_bytes": int(parts[1]),
                        "rx_packets": int(parts[2]),
                        "rx_errors": int(parts[3]),
                        "tx_bytes": int(parts[9]),
                        "tx_packets": int(parts[10]),
                        "tx_errors": int(parts[11])
                    }
            
            return {"error": f"Interface {iface} not found"}
        except Exception as e:
            self.logger(f"Error getting counters for {iface}: {e}")
            return {"error": str(e)}


    # === Network Controlling ===
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
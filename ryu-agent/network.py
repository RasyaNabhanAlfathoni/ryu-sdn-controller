import os
import subprocess
import re

class ServerNetworkDriver:
    def __init__(self, logger=print):
        self.logger = logger

    # === Network Monitoring ===

    def list_interfaces(self):
        # Mendapatkan daftar semua interface jaringan
        interfaces = os.listdir("/sys/class/net/")
        return [iface for iface in interfaces if iface != "lo"]

    def get_interface_details(self):
        interfaces = self.list_interfaces()
        result = []
        for iface in interfaces:
            info = self.get_ip_info(iface)
            status = subprocess.getoutput(f"cat /sys/class/net/{iface}/operstate").strip()
            info["status"] = status
            result.append(info)
        return result

    def get_interface_status(self, iface):
        # Get interface status using multiple methods
        try:
            # Method: Gunakan ip command
            ip_output = subprocess.getoutput(f"ip link show {iface}")
            if 'state UP' in ip_output:
                return 'up'
            elif 'state DOWN' in ip_output:
                return 'down'

        except Exception as e:
            self.logger(f"Error getting status for {iface}: {e}")
            return 'unknown'

    def get_ip_info(self, iface):
        # Ambil IP address dari masing-masing interface
        try:
            output = subprocess.getoutput(f"ip addr show {iface}")
            ip_match = re.findall(r'inet (\d+\.\d+\.\d+\.\d+/\d+)', output)
            mac_match = re.search(r'link/ether ([\da-f:]+)', output)
            mac = mac_match.group(1) if mac_match else "unknown"

            return {
                "interface": iface,
                "ip_addresses": ip_match,
                "mac_address": mac
            }
        except Exception as e:
            return {"interface": iface, "error": str(e)}
        
    def show_all(self):
        # Menampilkan seluruh interface beserta IP
        all_ifaces = self.list_interfaces()
        return [self.get_ip_info(i) for i in all_ifaces]

    def get_interface_ips(self, iface):
        # Menampilkan IP address spesifik dari interface untuk dropdown
        info = self.get_ip_info(iface)
        return info.get("ip_addresses", [])

    def get_routing_table(self):
        """Get routing table"""
        try:
            output = subprocess.getoutput("ip route show")
            routes = output.splitlines()
            return routes
        except Exception as e:
            self.logger(f"Error getting routing table: {e}")
            return {"error": str(e)}

    def get_arp_table(self):
        # Get ARP table
        try:
            output = subprocess.getoutput("ip neighbor show")
            neighbors = output.splitlines()
            return neighbors
        except Exception as e:
            self.logger(f"Error getting ARP table: {e}")
            return {"error": str(e)}

    def port_scan(self, target, ports=None):
        # Port scanning
        try:
            if ports:
                cmd = f"nmap -p {ports} {target}"
            else:
                cmd = f"nmap {target}"
            
            output = subprocess.getoutput(cmd)
            return output
        except Exception as e:
            self.logger(f"Error in port scan: {e}")
            return {"error": str(e)}
        
    def get_network_connections(self):
        # Get only listening ports
        try:
            # Hanya ambil listening ports saja (yang penting untuk server)
            output = subprocess.getoutput("ss -tunlp | grep LISTEN")
            connections = []
            
            for line in output.splitlines():
                parts = line.split()
                if len(parts) >= 6:
                    conn_info = {
                        "protocol": "tcp",
                        "local_address": parts[4],
                        "process": parts[-1] if "users:(" in parts[-1] else ""
                    }
                    connections.append(conn_info)
            
            return connections
            
        except Exception as e:
            self.logger(f"Error getting simple connections: {e}")
            return {"error": str(e)}

    def get_interface_counters(self, iface):
        # Basic interface stats
        try:
            # ambil data dari /proc/net/dev
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()
            
            for line in lines[2:]:  # Skip headers
                parts = line.split()
                if parts[0].strip(':') == iface:
                    return {
                        "interface": iface,
                        "rx_bytes": int(parts[1]),
                        "rx_packets": int(parts[2]),
                        "tx_bytes": int(parts[9]),
                        "tx_packets": int(parts[10])
                    }
            
            return {"error": f"Interface {iface} not found"}
            
        except Exception as e:
            self.logger(f"Error getting simple counters for {iface}: {e}")
            return {"error": str(e)}


    # === Network Controlling ===

    def add_ip(self, iface, ip_cidr):
        # Tambah IP ke interface tertentu
        cmd = f"ip addr add {ip_cidr} dev {iface}"
        return subprocess.getoutput(cmd)

    def del_ip(self, iface, ip_cidr):
        # Hapus IP dari interface tertentu
        cmd = f"ip addr del {ip_cidr} dev {iface}"
        return subprocess.getoutput(cmd)

    def enable_iface(self, iface):
        # Enable status interface
        return subprocess.getoutput(f"ip link set {iface} up")

    def disable_iface(self, iface):
        # Disable status interface
        return subprocess.getoutput(f"ip link set {iface} down")

   

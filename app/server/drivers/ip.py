import os
import subprocess
import re

class ServerIpDriver:
    def __init__(self, logger=print):
        self.logger = logger

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

    def get_ip_info(self, iface):
        # Ambil IP address dari interface
        try:
            output = subprocess.getoutput(f"ip addr show {iface}")
            ip_match = re.findall(r'inet (\d+\.\d+\.\d+\.\d+/\d+)', output)
            return {"interface": iface, "ip_addresses": ip_match}
        except Exception as e:
            return {"interface": iface, "error": str(e)}

    def add_ip(self, iface, ip_cidr):
        # Tambah IP ke interface tertentu
        cmd = f"ip addr add {ip_cidr} dev {iface}"
        return subprocess.getoutput(cmd)

    def del_ip(self, iface, ip_cidr):
        # Hapus IP dari interface
        cmd = f"ip addr del {ip_cidr} dev {iface}"
        return subprocess.getoutput(cmd)

    def enable_iface(self, iface):
        # Enable interface
        return subprocess.getoutput(f"ip link set {iface} up")

    def disable_iface(self, iface):
        # Disable interface
        return subprocess.getoutput(f"ip link set {iface} down")

    def show_all(self):
        # Menampilkan seluruh interface beserta IP
        all_ifaces = self.list_interfaces()
        return [self.get_ip_info(i) for i in all_ifaces]

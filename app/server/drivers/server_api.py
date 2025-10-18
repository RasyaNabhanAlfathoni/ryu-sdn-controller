import psutil, socket, netifaces, subprocess, platform, uuid

class ServerAPI:
    name = "ServerLocalAPI"

    def __init__(self, dev):
        self.ip = dev.get("ip")
        self.hostname = socket.gethostname()

    def get_main_ip(self):
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                ip = addrs[netifaces.AF_INET][0]['addr']
                if not ip.startswith("127."):
                    return ip
        return "127.0.0.1"

    def get_basic_info(self):
        return {
            "role": "manager",  # Tambahan: biar beda dari agent
            "hostname": self.hostname,
            "interfaces": netifaces.interfaces(),
            "ip": self.ip,
            "os": self.get_os_info(),
            "mac_address": self.get_mac_address(),
            "southbound": "ryu_manager_local",
            "meta": {
                "detected_ips": self.get_all_ips()
            }
        }
    
    def get_all_ips(self):
        ips = {}
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface)
            ipv4 = addrs.get(netifaces.AF_INET, [])
            if ipv4:
                ips[iface] = [addr['addr'] for addr in ipv4]
        return ips
    
    def get_mac_address(self):
        mac_num = uuid.getnode()
        return ':'.join(['{:02x}'.format((mac_num >> ele) & 0xff)
                        for ele in range(0,8*6,8)][::-1])

    def get_os_info(self):
        return f"{platform.system()} {platform.release()}"

    @staticmethod
    def get_utilization(logger=None):
        data = {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory().percent,
            "storage_usage": psutil.disk_usage('/').percent,
            "io_read": psutil.disk_io_counters().read_bytes,
            "io_write": psutil.disk_io_counters().write_bytes,
            "net_rx": psutil.net_io_counters().bytes_recv,
            "net_tx": psutil.net_io_counters().bytes_sent,
        }
        if logger: logger(f"Utilization Data: {data}")
        return data

    def get_logs(self, n=50):
        try:
            lines = subprocess.check_output(["tail", "-n", str(n), "/var/log/syslog"]).decode()
            return lines.splitlines()
        except Exception as e:
            return [str(e)]
import psutil, socket, netifaces, subprocess, platform, uuid

class ServerAPI:
    name = "ServerLocalAPI"

    def __init__(self, dev):
        self.ip = dev.get("ip")
        self.hostname = socket.gethostname()

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
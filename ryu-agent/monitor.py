# ryu-agent/monitor.py
import psutil
import platform
import subprocess

class MonitorDriver:
    def __init__(self, logger=print):
        self.logger = logger

    def get_utilization(self):
        """Get system utilization"""
        try:
            return {
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory().percent,
                "storage_usage": psutil.disk_usage('/').percent,
                "io_read": psutil.disk_io_counters().read_bytes,
                "io_write": psutil.disk_io_counters().write_bytes,
                "net_rx": psutil.net_io_counters().bytes_recv,
                "net_tx": psutil.net_io_counters().bytes_sent,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_system_info(self):
        """Get system information"""
        try:
            uname = platform.uname()
            return {
                "system": f"{uname.system} {uname.release}",
                "hostname": uname.node,
                "architecture": uname.machine,
                "processor": uname.processor,
                "boot_time": psutil.boot_time(),
                "users": [u.name for u in psutil.users()]
            }
        except Exception as e:
            return {"error": str(e)}

    def get_detailed_utilization(self):
        """Get detailed system utilization"""
        try:
            # CPU details
            cpu_times = psutil.cpu_times_percent(interval=1)
            
            # Memory details
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk details
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network details
            net_io = psutil.net_io_counters()
            
            return {
                "cpu": {
                    "percent": psutil.cpu_percent(interval=1),
                    "user": cpu_times.user,
                    "system": cpu_times.system,
                    "idle": cpu_times.idle,
                    "cores": psutil.cpu_count(logical=False),
                    "threads": psutil.cpu_count(logical=True)
                },
                "memory": {
                    "percent": memory.percent,
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2)
                },
                "swap": {
                    "percent": swap.percent,
                    "used_gb": round(swap.used / (1024**3), 2),
                    "total_gb": round(swap.total / (1024**3), 2)
                },
                "disk": {
                    "percent": disk.percent,
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes
                },
                "network": {
                    "bytes_recv": net_io.bytes_recv,
                    "bytes_sent": net_io.bytes_sent,
                    "packets_recv": net_io.packets_recv,
                    "packets_sent": net_io.packets_sent
                }
            }
        except Exception as e:
            return {"error": str(e)}
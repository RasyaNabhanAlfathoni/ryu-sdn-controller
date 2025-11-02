import psutil
import platform
import subprocess
import os
from datetime import datetime
from utils import detect_os_family, execute_command

class ServerSystemDriver:
    def __init__(self, logger=print):
        self.logger = logger
        self.os_family = detect_os_family()
        self._execute_command = execute_command
        self.logger(f"Detected OS: {self.os_family}")

    def get_utilization(self):
        """Get basic system utilization"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net_io = psutil.net_io_counters()
            disk_io = psutil.disk_io_counters()

            return {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "storage_usage": disk.percent,
                "io_read": disk_io.read_bytes if disk_io else 0,
                "io_write": disk_io.write_bytes if disk_io else 0,
                "net_rx": net_io.bytes_recv if net_io else 0,
                "net_tx": net_io.bytes_sent if net_io else 0,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_system_info(self):
        """Get comprehensive system information"""
        try:
            uname = platform.uname()
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            
            # Get OS specific info
            os_info = self._get_os_specific_info()
            kernel_version = platform.release()
            
            return {
                "system": f"{uname.system} {uname.release}",
                "hostname": uname.node,
                "architecture": uname.machine,
                "processor": uname.processor,
                "kernel_version": kernel_version,
                "boot_time": boot_time.isoformat(),
                "uptime": str(datetime.now() - boot_time),
                "users": [u.name for u in psutil.users()],
                "os_family": self.os_family,
                "os_details": os_info
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_os_specific_info(self):
        """Get OS-specific information"""
        try:
            if self.os_family in ['debian', 'ubuntu']:
                # Debian/Ubuntu
                result = self._execute_command("lsb_release -d")
                if result["success"]:
                    return {"description": result["stdout"].split(":")[1].strip()}
            elif self.os_family in ['rhel', 'centos']:
                # RHEL/CentOS
                with open("/etc/redhat-release", "r") as f:
                    return {"description": f.read().strip()}
            elif self.os_family == 'fedora':
                # Fedora
                with open("/etc/fedora-release", "r") as f:
                    return {"description": f.read().strip()}
            elif self.os_family == 'suse':
                # openSUSE/SLES
                with open("/etc/SuSE-release", "r") as f:
                    return {"description": f.read().strip()}
        except Exception:
            pass
        
        # Fallback
        with open("/etc/os-release", "r") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return {"description": line.split("=")[1].strip().strip('"')}
        
        return {"description": "Unknown"}

    def get_detailed_utilization(self):
        """Get detailed system utilization"""
        try:
            # CPU
            cpu_times = psutil.cpu_times_percent(interval=1)
            cpu_freq = psutil.cpu_freq()
            per_core = psutil.cpu_percent(interval=1, percpu=True)

            # Memory
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Disk
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            partitions = [
                {
                    "device": p.device,
                    "mount": p.mountpoint,
                    "fs_type": p.fstype,
                    "usage_percent": psutil.disk_usage(p.mountpoint).percent
                }
                for p in psutil.disk_partitions()
            ]

            # Network
            net_io = psutil.net_io_counters()
            net_per_iface = {
                iface: {
                    "bytes_recv": stats.bytes_recv,
                    "bytes_sent": stats.bytes_sent,
                    "packets_recv": stats.packets_recv,
                    "packets_sent": stats.packets_sent,
                }
                for iface, stats in psutil.net_io_counters(pernic=True).items()
            }

            # Load Average
            load_avg = os.getloadavg()

            # Top Processes (by CPU)
            top_processes = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = p.info
                    top_processes.append(info)
                except Exception:
                    continue
            top_processes = sorted(top_processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]

            # Temperature (if supported)
            try:
                temps = psutil.sensors_temperatures()
            except Exception:
                temps = {}

            return {
                "cpu": {
                    "percent": psutil.cpu_percent(interval=1),
                    "user": getattr(cpu_times, 'user', 0),
                    "system": getattr(cpu_times, 'system', 0),
                    "idle": getattr(cpu_times, 'idle', 0),
                    "cores": psutil.cpu_count(logical=False),
                    "threads": psutil.cpu_count(logical=True),
                    "frequency": cpu_freq.current if cpu_freq else "unknown",
                    "load_avg": load_avg,
                    "per_core_percent": per_core
                },
                "memory": {
                    "percent": memory.percent,
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                    "cached_gb": round(getattr(memory, 'cached', 0) / (1024**3), 2),
                    "buffers_gb": round(getattr(memory, 'buffers', 0) / (1024**3), 2)
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
                    "read_bytes": disk_io.read_bytes if disk_io else 0,
                    "write_bytes": disk_io.write_bytes if disk_io else 0,
                    "read_count": disk_io.read_count if disk_io else 0,
                    "write_count": disk_io.write_count if disk_io else 0,
                    "partitions": partitions
                },
                "network": {
                    "bytes_recv": net_io.bytes_recv if net_io else 0,
                    "bytes_sent": net_io.bytes_sent if net_io else 0,
                    "packets_recv": net_io.packets_recv if net_io else 0,
                    "packets_sent": net_io.packets_sent if net_io else 0,
                    "interfaces": net_per_iface
                },
                "temperature": temps,
                "top_processes": top_processes
            }
        except Exception as e:
            return {"error": str(e)}

    def get_system_logs(self, n=50):
        """Get system logs - compatible dengan berbagai distro"""
        log_files = []
        
        # Determine log file based on OS
        if self.os_family in ['debian', 'ubuntu']:
            log_files = ["/var/log/syslog", "/var/log/messages"]
        elif self.os_family in ['rhel', 'centos', 'fedora']:
            log_files = ["/var/log/messages", "/var/log/syslog"]
        elif self.os_family == 'suse':
            log_files = ["/var/log/messages"]
        else:
            log_files = ["/var/log/syslog", "/var/log/messages"]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    result = self._execute_command(f"tail -n {n} {log_file}")
                    if result["success"]:
                        return result["stdout"].splitlines()
                except Exception:
                    continue
        
        # Fallback to journalctl if available
        try:
            result = self._execute_command(f"journalctl -n {n} --no-pager")
            if result["success"]:
                return result["stdout"].splitlines()
        except Exception:
            pass
        
        return {"error": "Could not access system logs"}

    def get_dmesg_logs(self, n=50):
        """Get kernel logs"""
        try:
            result = self._execute_command(f"dmesg -T | tail -n {n}")
            if result["success"]:
                return result["stdout"].splitlines()
            else:
                # Fallback without -T flag
                result = self._execute_command(f"dmesg | tail -n {n}")
                if result["success"]:
                    return result["stdout"].splitlines()
                else:
                    return {"error": result.get("error", result["stderr"])}
        except Exception as e:
            self.logger(f"Error getting dmesg logs: {e}")
            return {"error": str(e)}
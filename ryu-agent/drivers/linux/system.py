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

    def _get_hardware_info(self):
        """Collect detailed hardware information (CPU, virtualization, etc.)"""
        info = {}

        # === BOARD ARCHITECTURE ===
        try:
            info["architecture"] = platform.machine()
            info["cpu_bits"] = "64-bit" if platform.machine().endswith("64") else "32-bit"
        except:
            info["architecture"] = "Unknown"
            info["cpu_bits"] = "Unknown"

        # === CPU MODEL ===
        try:
            cpu_model = None
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "model name" in line:
                            cpu_model = line.split(":")[1].strip()
                            break
            info["cpu_model"] = cpu_model or platform.processor() or "Unknown"
        except:
            info["cpu_model"] = "Unknown"

        # === VIRTUALIZATION DETECTION ===
        info["virtualization"] = {
            "is_virtual_machine": False,
            "virtual_type": None
        }

        # systemd-detect-virt (lebih akurat)
        try:
            result = subprocess.run(
                 ["systemd-detect-virt"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            virt_type = result.stdout.strip()
            if virt_type and virt_type != "none":
                info["virtualization"]["is_virtual_machine"] = True
                info["virtualization"]["virtual_type"] = virt_type
        except:
            pass

        # === BIOS / MOTHERBOARD INFO ===
        try:
            dmi = "/sys/class/dmi/id/"

            def read_dmi(file):
                path = os.path.join(dmi, file)
                if os.path.exists(path):
                    return open(path).read().strip()
                return None

            info["hardware_vendor"] = read_dmi("sys_vendor")
            info["hardware_model"] = read_dmi("product_name")
            info["bios_version"] = read_dmi("bios_version")
            info["bios_date"] = read_dmi("bios_date")
        except:
            pass

        return info

    def get_detailed_utilization(self):
        """Get detailed system utilization - FIXED VERSION"""
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
            # FIX: Filter partitions yang meaningful
            partitions = []
            for p in psutil.disk_partitions():
                try:
                    # Skip virtual/docker mounts dan filesystem types tertentu
                    if any(skip in p.mountpoint for skip in [
                        '/etc/', '/proc/', '/sys/', '/dev/', '/run/',
                        '/var/lib/docker/', '/snap/'
                    ]):
                        continue
                        
                    # Skip certain filesystem types
                    if p.fstype in ['squashfs', 'overlay', 'tmpfs', 'devtmpfs']:
                        continue
                        
                    usage = psutil.disk_usage(p.mountpoint)
                    partitions.append({
                        "device": p.device,
                        "mount": p.mountpoint,
                        "fs_type": p.fstype,
                        "usage_percent": round(usage.percent, 1),
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2)
                    })
                except (PermissionError, OSError) as e:
                    # Skip partitions yang tidak bisa diakses
                    self.logger(f"Skipping partition {p.mountpoint}: {e}")
                    continue

            # Network
            net_io = psutil.net_io_counters()
            net_per_iface = {}
            
            try:
                # FIX: Handle case where pernic=True might fail
                interface_stats = psutil.net_io_counters(pernic=True)
                for iface, stats in interface_stats.items():
                    # Skip virtual interfaces
                    if any(virtual in iface for virtual in ['virbr', 'docker', 'veth', 'br-']):
                        continue
                        
                    net_per_iface[iface] = {
                        "bytes_recv": stats.bytes_recv,
                        "bytes_sent": stats.bytes_sent,
                        "packets_recv": stats.packets_recv,
                        "packets_sent": stats.packets_sent,
                        "errin": stats.errin,
                        "errout": stats.errout,
                        "dropin": stats.dropin,
                        "dropout": stats.dropout
                    }
            except Exception as e:
                self.logger(f"Network per-interface stats failed: {e}")
                # Fallback to aggregate stats only

            # Load Average
            load_avg = os.getloadavg()

            # Top Processes
            top_processes = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
                try:
                    info = p.info
                    # Convert memory to MB untuk consistency
                    if info.get('memory_info'):
                        info['memory_mb'] = round(info['memory_info'].rss / (1024**2), 1)
                    top_processes.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU then memory
            top_processes = sorted(
                top_processes, 
                key=lambda x: (x.get('cpu_percent', 0), x.get('memory_percent', 0)), 
                reverse=True
            )[:10]  # Top 10 processes

            # Temperature
            try:
                temps = psutil.sensors_temperatures()
                # Simplify temperature data
                simplified_temps = {}
                for sensor, readings in temps.items():
                    if readings:
                        simplified_temps[sensor] = {
                            'current': readings[0].current,
                            'high': readings[0].high,
                            'critical': readings[0].critical
                        }
                temps = simplified_temps
            except Exception:
                temps = {}

            return {
                "hardware" : self._get_hardware_info(),
                "cpu": {
                    "percent": psutil.cpu_percent(interval=1),
                    "user": round(getattr(cpu_times, 'user', 0), 1),
                    "system": round(getattr(cpu_times, 'system', 0), 1),
                    "idle": round(getattr(cpu_times, 'idle', 0), 1),
                    "cores": psutil.cpu_count(logical=False),
                    "threads": psutil.cpu_count(logical=True),
                    "frequency": round(cpu_freq.current, 1) if cpu_freq else 0,
                    "load_avg": [round(load, 3) for load in load_avg],
                    "per_core_percent": [round(pct, 1) for pct in per_core]
                },
                "memory": {
                    "percent": round(memory.percent, 1),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                    "cached_gb": round(getattr(memory, 'cached', 0) / (1024**3), 2),
                    "buffers_gb": round(getattr(memory, 'buffers', 0) / (1024**3), 2),
                    "shared_gb": round(getattr(memory, 'shared', 0) / (1024**3), 2)
                },
                "swap": {
                    "percent": round(swap.percent, 1),
                    "used_gb": round(swap.used / (1024**3), 2),
                    "total_gb": round(swap.total / (1024**3), 2),
                    "sin": round(swap.sin / (1024**2), 1) if hasattr(swap, 'sin') else 0,
                    "sout": round(swap.sout / (1024**2), 1) if hasattr(swap, 'sout') else 0
                },
                "disk": {
                    "root": {
                        "percent": round(disk.percent, 1),
                        "used_gb": round(disk.used / (1024**3), 2),
                        "free_gb": round(disk.free / (1024**3), 2),
                        "total_gb": round(disk.total / (1024**3), 2)
                    },
                    "io": {
                        "read_bytes": disk_io.read_bytes if disk_io else 0,
                        "write_bytes": disk_io.write_bytes if disk_io else 0,
                        "read_count": disk_io.read_count if disk_io else 0,
                        "write_count": disk_io.write_count if disk_io else 0
                    },
                    "partitions": partitions
                },
                "network": {
                    "total": {
                        "bytes_recv": net_io.bytes_recv if net_io else 0,
                        "bytes_sent": net_io.bytes_sent if net_io else 0,
                        "packets_recv": net_io.packets_recv if net_io else 0,
                        "packets_sent": net_io.packets_sent if net_io else 0
                    },
                    "interfaces": net_per_iface
                },
                "temperature": temps,
                "top_processes": top_processes
            }
        except Exception as e:
            self.logger(f"Error in get_detailed_utilization: {e}")
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
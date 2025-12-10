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

    def health_check(self, detailed=False):
        """Basic health check untuk server agent"""
        try:            
            # Uptime
            uptime_seconds = psutil.boot_time()
            uptime_str = str(datetime.timedelta(seconds=uptime_seconds))
            
            # 3. Determine overall status
            overall_status = "healthy"
            issues = []
            
            # 4. Basic response (untuk detailed=False)
            if not detailed:
                return {
                    "status": "ok",
                    "health": overall_status,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "uptime": uptime_str,
                    "issues": issues if issues else None
                }
            

        except ImportError:
            # Jika psutil tidak tersedia
            return {
                "status": "error",
                "health": "unknown",
                "timestamp": datetime.datetime.now().isoformat(),
                "error": "psutil module not available",
                "message": "Install psutil: pip install psutil"
            }
            
        except Exception as e:
            self.logger(f"Health check error: {e}")
            return {
                "status": "error",
                "health": "unknown",
                "timestamp": datetime.datetime.now().isoformat(),
                "error": str(e)
            }

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
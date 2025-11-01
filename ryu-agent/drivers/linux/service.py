import subprocess
import psutil
import json
import os
from utils import detect_os_family, execute_command

class ServerServiceDriver:
    def __init__(self, logger=print):
        self.logger = logger
        self.os_family = detect_os_family()
        self._execute_command = execute_command
        self.init_system = self.detect_init_system()
        self.logger(f"Detected OS: {self.os_family}, Init: {self.init_system}")

    def detect_init_system(self):
        """Detect init system"""
        try:
            # Check systemd (most modern distros)
            result = subprocess.run(["systemctl", "--version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return 'systemd'
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Check Upstart (older Ubuntu)
        try:
            result = subprocess.run(["initctl", "--version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return 'upstart'
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Check SysV init (legacy)
        if os.path.exists("/etc/init.d"):
            return 'sysvinit'

        return 'unknown'

    def list_services(self):
        """List services based on init system"""
        try:
            if self.init_system == 'systemd':
                # Use systemctl for modern systems
                cmd = "systemctl list-units --type=service --all --no-legend"
                result = self._execute_command(cmd)
                
                if not result["success"]:
                    return {"error": result.get("error", result["stderr"])}
                
                services = []
                for line in result["stdout"].splitlines():
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 4:
                            service = {
                                "name": parts[0],
                                "load": parts[1],
                                "active": parts[2],
                                "sub": parts[3],
                                "description": " ".join(parts[4:]) if len(parts) > 4 else ""
                            }
                            services.append(service)
                return services
                
            elif self.init_system == 'sysvinit':
                # Use service --status-all for SysV
                cmd = "service --status-all"
                result = self._execute_command(cmd)
                
                if not result["success"]:
                    return {"error": result.get("error", result["stderr"])}
                
                services = []
                for line in result["stdout"].splitlines():
                    if '[' in line and ']' in line:
                        status_char = line[line.find('[')+1:line.find(']')]
                        service_name = line[line.find(']')+1:].strip()
                        
                        status_map = {'+': 'running', '-': 'stopped', '?': 'unknown'}
                        services.append({
                            "name": service_name,
                            "active": status_map.get(status_char, 'unknown'),
                            "load": "loaded",
                            "sub": "active" if status_char == '+' else "inactive"
                        })
                return services
                
            else:
                return {"error": f"Unsupported init system: {self.init_system}"}
                
        except Exception as e:
            return {"error": str(e)}

    def service_control(self, service, action):
        """Control service based on init system"""
        valid_actions = ["start", "stop", "restart", "enable", "disable", "reload"]
        if action not in valid_actions:
            return {"error": f"Invalid action. Use: {valid_actions}"}
        
        try:
            if self.init_system == 'systemd':
                cmd = f"systemctl {action} {service}"
            elif self.init_system == 'sysvinit':
                if action in ['enable', 'disable']:
                    # SysV doesn't have native enable/disable, use update-rc.d or chkconfig
                    if self.os_family in ['debian', 'ubuntu']:
                        if action == 'enable':
                            cmd = f"update-rc.d {service} enable"
                        else:
                            cmd = f"update-rc.d {service} disable"
                    elif self.os_family in ['rhel', 'centos']:
                        if action == 'enable':
                            cmd = f"chkconfig {service} on"
                        else:
                            cmd = f"chkconfig {service} off"
                    else:
                        return {"error": f"Enable/disable not supported for {self.os_family} with SysV"}
                else:
                    cmd = f"service {service} {action}"
            else:
                return {"error": f"Unsupported init system: {self.init_system}"}
            
            result = self._execute_command(cmd)
            if result["success"]:
                return {"status": "success", "output": result["stdout"]}
            else:
                return {"error": result.get("error", result["stderr"])}
                
        except Exception as e:
            return {"error": str(e)}

    def service_status(self, service):
        """Get detailed service status"""
        try:
            if self.init_system == 'systemd':
                # Get service status
                status_cmd = f"systemctl is-active {service}"
                status_result = self._execute_command(status_cmd)
                status = status_result["stdout"] if status_result["success"] else "unknown"
                
                # Get detailed info
                info_cmd = f"systemctl show {service} --property=LoadState,ActiveState,SubState,MainPID"
                info_result = self._execute_command(info_cmd)
                
                info = {}
                if info_result["success"]:
                    for line in info_result["stdout"].splitlines():
                        if "=" in line:
                            key, value = line.split("=", 1)
                            info[key.lower()] = value
                
                return {
                    "service": service,
                    "status": status,
                    "loaded": info.get("loadstate", "unknown"),
                    "active": info.get("activestate", "unknown"),
                    "substate": info.get("substate", "unknown"),
                    "pid": info.get("mainpid", "unknown"),
                    "init_system": self.init_system
                }
                
            elif self.init_system == 'sysvinit':
                # Simple status for SysV
                cmd = f"service {service} status"
                result = self._execute_command(cmd)
                
                return {
                    "service": service,
                    "status": "active" if result["success"] else "inactive",
                    "output": result["stdout"],
                    "init_system": self.init_system
                }
                
            else:
                return {"error": f"Unsupported init system: {self.init_system}"}
                
        except Exception as e:
            return {"error": str(e)}
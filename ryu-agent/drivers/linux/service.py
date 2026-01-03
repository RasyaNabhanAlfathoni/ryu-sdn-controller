import subprocess
import psutil
import json
import os
from utils import detect_os_family, execute_command, execute_on_host, execute_on_ssh

class ServerServiceDriver:
    def __init__(self, logger=print):
        self.logger = logger
        os_info = detect_os_family()
        self.os_family = os_info.get('family', 'unknown')
        self._execute_command = execute_command
        self._execute_on_host = execute_on_host
        self._execute_on_ssh = execute_on_ssh
        self.init_system = self.detect_init_system()
        self.logger(f"Detected OS: {self.os_family}, Init: {self.init_system}")

    def _execute(self, cmd, use_ssh=False):
        """Wrapper untuk execute command dengan pilihan SSH"""
        try:
            if use_ssh:
                return self._execute_on_ssh(cmd)
            else:
                return self._execute_on_host(cmd)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def detect_init_system(self):
        """Detect init system"""
        try:
            # Check systemd
            result = self._execute("systemctl --version", use_ssh=True)
            if result["success"]:
                return 'systemd'
        except Exception:
            pass

        # Check Upstart
        try:
            result = self._execute("initctl --version", use_ssh=False)
            if result["success"]:
                return 'upstart'
        except Exception:
            pass

        # Check SysV init
        result = self._execute("[ -d /etc/init.d ] && echo 'exists'", use_ssh=False)
        if result["success"] and result["stdout"] == "exists":
            return 'sysvinit'

        return 'unknown'

    def list_services(self):
        """List services from HOST (read-only operation, bisa pakai chroot)"""
        try:
            if self.init_system == 'systemd':
                # Use systemctl (read-only, aman pakai chroot)
                cmd = "systemctl list-units --type=service --all --no-legend"
                result = self._execute(cmd, use_ssh=True)
                
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
                # Use service --status-all (read-only)
                cmd = "service --status-all"
                result = self._execute(cmd, use_ssh=False)
                
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
        """Control service (gunakan SSH untuk write operations)"""
        valid_actions = ["start", "stop", "restart", "enable", "disable", "reload"]
        if action not in valid_actions:
            return {"error": f"Invalid action. Use: {valid_actions}"}
        
        try:
            cmd = ""
            use_ssh = True  # Default pakai SSH untuk semua control operations
            
            if self.init_system == 'systemd':
                # Systemctl butuh D-Bus, pakai SSH
                cmd = f"systemctl {action} {service}"
                use_ssh = True
                
            elif self.init_system == 'sysvinit':
                if action in ['enable', 'disable']:
                    # SysV enable/disable butuh write ke runlevels, pakai SSH
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
                    use_ssh = True
                else:
                    # start/stop/restart bisa coba chroot dulu, fallback ke SSH
                    cmd = f"service {service} {action}"
                    # Coba dulu dengan chroot
                    result = self._execute(cmd, use_ssh=False)
                    if result["success"]:
                        return {"status": "success", "output": result["stdout"], "method": "chroot"}
                    else:
                        # Fallback ke SSH
                        use_ssh = True
            else:
                return {"error": f"Unsupported init system: {self.init_system}"}
            
            result = self._execute(cmd, use_ssh=use_ssh)
            if result["success"]:
                method = "ssh" if use_ssh else "chroot"
                return {"status": "success", "output": result["stdout"], "method": method}
            else:
                return {"error": result.get("error", result["stderr"])}
                
        except Exception as e:
            return {"error": str(e)}

    def service_status(self, service):
        """Get detailed service status from HOST (read-only, bisa pakai chroot)"""
        try:
            if self.init_system == 'systemd':
                # Get service status (read-only, aman pakai chroot)
                status_cmd = f"systemctl is-active {service}"
                status_result = self._execute(status_cmd, use_ssh=True)
                status = status_result["stdout"] if status_result["success"] else "unknown"
                
                # Get detailed info (read-only)
                info_cmd = f"systemctl show {service} --property=LoadState,ActiveState,SubState,MainPID"
                info_result = self._execute(info_cmd, use_ssh=True)
                
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
                # Simple status for SysV (read-only)
                cmd = f"service {service} status"
                result = self._execute(cmd, use_ssh=False)
                
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
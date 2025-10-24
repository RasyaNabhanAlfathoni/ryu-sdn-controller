import subprocess
import psutil
import json

class ServiceDriver:
    def __init__(self, logger=print):
        self.logger = logger

    def list_services(self):
        # List semua system services menggunakan systemctl
        try:
            # Get all services in Agent
            cmd = "systemctl list-units --type=service --all --no-legend"
            output = subprocess.getoutput(cmd)
            
            services = []
            for line in output.splitlines():
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
        except Exception as e:
            return {"error": str(e)}

    def service_control(self, service, action):
        """Control service (start/stop/restart/enable/disable)"""
        valid_actions = ["start", "stop", "restart", "enable", "disable", "reload"]
        if action not in valid_actions:
            return {"error": f"Invalid action. Use: {valid_actions}"}
        
        try:
            cmd = f"systemctl {action} {service}"
            result = subprocess.getoutput(cmd)
            return {"status": "success", "output": result}
        except Exception as e:
            return {"error": str(e)}

    def service_status(self, service):
        # Get detailed service status
        try:
            # Get service status
            status_cmd = f"systemctl is-active {service}"
            status = subprocess.getoutput(status_cmd)
            
            # Get service info
            info_cmd = f"systemctl show {service} --property=LoadState,ActiveState,SubState,MainPID"
            info_output = subprocess.getoutput(info_cmd)
            
            info = {}
            for line in info_output.splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    info[key.lower()] = value
            
            return {
                "service": service,
                "status": status,
                "loaded": info.get("loadstate", "unknown"),
                "active": info.get("activestate", "unknown"),
                "substate": info.get("substate", "unknown"),
                "pid": info.get("mainpid", "unknown")
            }
        except Exception as e:
            return {"error": str(e)}
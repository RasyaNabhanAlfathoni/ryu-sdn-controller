import subprocess
import json
import re
from typing import Dict, List, Optional
from utils import execute_on_host, execute_command

class LLDPDriver:
    def __init__(self):
        self.lldpcli_path = "/usr/sbin/lldpcli"
    
    def _execute(self, cmd, use_host=True):
        """Execute command either"""
        try:
            if use_host:
                return execute_on_host(cmd)
            else:
                return execute_command(cmd)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_neighbors(self) -> Dict:
        """Get LLDP neighbors information"""
        try:
            # Execute lldpcli command
            cmd = f"{self.lldpcli_path} show neighbors -f json"
            result = self._execute(cmd, use_host=True)
            
            if result["success"]:
                try:
                    return json.loads(result["stdout"])
                except json.JSONDecodeError:
                    return {"error": "Invalid JSON response from LLDP", "raw_output": result["stdout"]}
            else:
                return {"error": result.get("stderr", result.get("error", "Unknown error"))}
                
        except Exception as e:
            return {"error": f"LLDP error: {str(e)}"}
    
    def get_interface_neighbors(self, iface: str) -> Dict:
        """Get LLDP neighbors for specific interface"""
        try:
            cmd = f"{self.lldpcli_path} show neighbors ports {iface} -f json"
            result = self._execute(cmd, use_host=True)
            
            if result["success"]:
                try:
                    return json.loads(result["stdout"])
                except json.JSONDecodeError:
                    return {"error": f"Invalid JSON for interface {iface}", "raw_output": result["stdout"]}
            else:
                return {"error": result.get("stderr", result.get("error", "Unknown error"))}
                
        except Exception as e:
            return {"error": f"Interface LLDP error: {str(e)}"}
    
    def get_lldp_statistics(self) -> Dict:
        """Get LLDP statistics"""
        try:
            cmd = f"{self.lldpcli_path} show statistics -f json"
            result = self._execute(cmd, use_host=True)
            
            if result["success"]:
                try:
                    return json.loads(result["stdout"])
                except json.JSONDecodeError:
                    return {"error": "Invalid JSON statistics", "raw_output": result["stdout"]}
            else:
                return {"error": result.get("stderr", result.get("error", "Unknown error"))}
                
        except Exception as e:
            return {"error": f"Statistics error: {str(e)}"}
    
    def get_lldp_status(self) -> Dict:
        """Get LLDP daemon status"""
        try:
            # Check if lldpd process is running
            cmd = "ps aux | grep lldpd | grep -v grep"
            result = self._execute(cmd, use_host=True)
            
            # Check if lldpd is in process list
            lldpd_running = result["success"] and result["stdout"] and "lldpd" in result["stdout"]
            status = "active" if lldpd_running else "inactive"
            
            # Count lldpd processes
            lldpd_processes = 0
            if result["success"] and result["stdout"]:
                lldpd_processes = len([line for line in result["stdout"].split('\n') 
                                     if line.strip() and 'lldpd' in line])
            
            # Check lldpcli availability
            check_cmd = f"which {self.lldpcli_path} || echo 'not_found'"
            lldpcli_check = self._execute(check_cmd, use_host=True)
            lldpcli_available = lldpcli_check["success"] and "not_found" not in lldpcli_check["stdout"]
            
            # Get lldpd user if running
            lldpd_user = "none"
            if lldpd_running and result["stdout"]:
                lines = result["stdout"].split('\n')
                for line in lines:
                    if line.strip() and 'lldpd' in line:
                        parts = line.split()
                        if len(parts) > 0:
                            lldpd_user = parts[0]
                            break
            
            return {
                "service_status": status,
                "lldpcli_available": lldpcli_available,
                "lldpcli_path": self.lldpcli_path,
                "lldpd_processes": lldpd_processes,
                "lldpd_user": lldpd_user,
                "running_on": "host"
            }
        except Exception as e:
            return {"error": f"Status check error: {str(e)}"}
import subprocess
import json
import re
from typing import Dict, List, Optional
from utils import execute_on_host, execute_command, execute_on_ssh

class LLDPDriver:
    def __init__(self):
        self.lldpcli_path = "/usr/sbin/lldpcli"
    
    def _execute(self, cmd, use_host=True, use_ssh=False):
        """Execute command dengan pilihan fungsi"""
        try:
            if use_ssh:
                return execute_on_ssh(cmd)
            elif use_host:
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
            # 1. Cek apakah lldpcli ada
            check_cmd = f"which {self.lldpcli_path} 2>/dev/null || command -v {self.lldpcli_path} 2>/dev/null || echo 'not_found'"
            lldpcli_check = self._execute(check_cmd, use_host=True)
            lldpcli_available = lldpcli_check["success"] and "not_found" not in lldpcli_check["stdout"]
            
            if not lldpcli_available:
                return {
                    "status": "error",
                    "error": f"LLDP CLI not found at {self.lldpcli_path}",
                    "lldpcli_available": False,
                    "service_status": "not_installed"
                }
            
            # Coba cek service dengan systemctl
            service_status = "unknown"
            service_active = False
            
            # Coba beberapa nama service yang mungkin
            service_names = ["lldpd", "lldpd.service", "lldp"]
            
            for service_name in service_names:
                # Coba via SSH dulu (lebih reliable untuk service management)
                cmd_check = f"systemctl is-active {service_name} 2>/dev/null"
                result = self._execute(cmd_check, use_ssh=True)
                
                service_status = result["stdout"].strip()
                service_active = (service_status == "active")
                break
            
            # Hitung proses lldpd
            lldpd_processes = 0
            lldpd_user = "none"
            
            cmd_count = "pgrep -l lldpd 2>/dev/null | wc -l || echo '0'"
            count_result = self._execute(cmd_count, use_host=True)
            if count_result["success"]:
                try:
                    lldpd_processes = int(count_result["stdout"].strip())
                except:
                    lldpd_processes = 0
            
            # Dapatkan user yang menjalankan lldpd
            if lldpd_processes > 0:
                cmd_user = "ps -eo user,comm | grep lldpd | head -1 | awk '{print $1}' 2>/dev/null || echo 'unknown'"
                user_result = self._execute(cmd_user, use_host=True)
                if user_result["success"]:
                    lldpd_user = user_result["stdout"].strip()
            
            # Cek versi lldpd
            version_info = ""
            cmd_version = f"{self.lldpcli_path} -v || echo 'version_unknown'"
            version_result = self._execute(cmd_version, use_host=True)
            if version_result["success"] and "version_unknown" not in version_result["stdout"]:
                version_info = version_result["stdout"].strip()
            
            # Compile result
            result = {
                "status": "success",
                "data": {
                    "service_status": service_status,
                    "service_active": service_active,
                    "lldpcli_available": lldpcli_available,
                    "lldpcli_path": self.lldpcli_path,
                    "lldpd_processes": lldpd_processes,
                    "lldpd_user": lldpd_user,
                    "version": version_info,
                    "running_on": "host",
                    "health": "healthy" if service_active else "unhealthy",
                },
            }
            
            # Jika service tidak active, tambahkan debugging info
            if not service_active:
                # Coba dapatkan error logs
                cmd_journal = "journalctl -u lldpd --no-pager -n 5 2>/dev/null | tail -5 || echo 'no_journal'"
                journal_result = self._execute(cmd_journal, use_ssh=True)
                if journal_result["success"] and "no_journal" not in journal_result["stdout"]:
                    result["data"]["journal_logs"] = journal_result["stdout"].strip()
                
                # Coba dapatkan service status detail
                cmd_status = "systemctl status lldpd --no-pager 2>/dev/null | head -20 || echo 'no_status'"
                status_result = self._execute(cmd_status, use_ssh=True)
                if status_result["success"] and "no_status" not in status_result["stdout"]:
                    result["data"]["service_details"] = status_result["stdout"].strip()
            
            return result
            
        except Exception as e:
            import traceback
            return {
                "status": "error", 
                "error": f"Status check error: {str(e)}",
                "traceback": traceback.format_exc()
            }
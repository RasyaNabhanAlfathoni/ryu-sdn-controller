import subprocess
import json
import re
from typing import Dict, List, Optional

class LLDPDriver:
    def __init__(self):
        self.lldpcli_path = "/usr/sbin/lldpcli"
    
    def get_neighbors(self) -> Dict:
        """Get LLDP neighbors information"""
        try:
            # Execute lldpcli command
            result = subprocess.run(
                [self.lldpcli_path, "show", "neighbors", "-f", "json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {"error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"error": "LLDP command timeout"}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response from LLDP"}
        except FileNotFoundError:
            return {"error": "lldpcli not found"}
        except Exception as e:
            return {"error": f"LLDP error: {str(e)}"}
    
    def get_interface_neighbors(self, iface: str) -> Dict:
        """Get LLDP neighbors for specific interface"""
        try:
            result = subprocess.run(
                [self.lldpcli_path, "show", "neighbors", "ports", iface, "-f", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {"error": result.stderr}
                
        except Exception as e:
            return {"error": f"Interface LLDP error: {str(e)}"}
    
    def get_lldp_statistics(self) -> Dict:
        """Get LLDP statistics"""
        try:
            result = subprocess.run(
                [self.lldpcli_path, "show", "statistics", "-f", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {"error": result.stderr}
                
        except Exception as e:
            return {"error": f"Statistics error: {str(e)}"}
    
    def get_lldp_status(self) -> Dict:
        """Get LLDP daemon status"""
        try:
            # Check if lldpd process is running (search for any user)
            result = subprocess.run(
                ["ps", "aux"],  # Get all processes
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Check if lldpd is in process list
            lldpd_running = "lldpd" in result.stdout
            status = "active" if lldpd_running else "inactive"
            
            # Count lldpd processes
            lldpd_processes = len([line for line in result.stdout.split('\n') if 'lldpd' in line and 'grep' not in line])
            
            # Check lldpcli availability
            lldpcli_available = subprocess.run(["which", "lldpcli"], capture_output=True).returncode == 0
            
            return {
                "service_status": status,
                "lldpcli_available": lldpcli_available,
                "lldpcli_path": self.lldpcli_path,
                "lldpd_processes": lldpd_processes,
                "lldpd_user": "_lldpd" if lldpd_running else "none"
            }
        except Exception as e:
            return {"error": f"Status check error: {str(e)}"}
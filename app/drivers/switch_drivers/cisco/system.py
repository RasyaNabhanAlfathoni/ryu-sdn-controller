"""
Cisco System Operations - Discovery & Info
"""
import re
import json

class CiscoSystemDriver:
    def __init__(self, config):
        self.config = config
        self.base = None
    
    def set_base(self, base):
        """Set base SSH connection"""
        self.base = base
    
    def save_config(self, logger=None):
        """Save running configuration to startup"""
        try:
            if logger:
                logger("Saving configuration...")
            
            output = self.base.execute_command("write memory", enable_mode=True)
            
            if logger:
                logger("Configuration saved successfully")
            
            return {
                'status': 'success',
                'message': 'Configuration saved successfully',
                'output': output[:200]
            }
            
        except Exception as e:
            if logger:
                logger(f"Error saving config: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def reboot(self, logger=None, confirm=False, user="system"):
        if not confirm:
            return {
                "status": "error",
                "error": "reboot requires explicit confirmation"
            }

        try:
            if logger:
                logger({
                    "event": "reboot",
                    "user": user,
                    "status": "initiated"
                })

            self.save_config(logger)

            self.base.execute_command("reload", enable_mode=True)

            return {
                "status": "success",
                "message": "Reboot command sent"
            }

        except Exception as e:
            if logger:
                logger({
                    "event": "reboot",
                    "status": "failed",
                    "error": str(e)
                })

            return {"status": "error", "error": str(e)}
    
    def get_running_config(self, logger=None):
        try:
            raw = self.base.execute_command("show running-config", enable_mode=True)

            # HIDE SECRET
            sanitized = re.sub(
                r'(password|secret) .*',
                r'\1 <hidden>',
                raw
            )

            return {
                "status": "success",
                "size": len(sanitized),
                "config": sanitized
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

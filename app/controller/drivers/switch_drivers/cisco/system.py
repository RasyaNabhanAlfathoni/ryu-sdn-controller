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
        """Reboot Cisco switch"""
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
        """Get Cisco switch running config"""
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

    def set_identity(self, hostname, logger=None):
        """Set Cisco switch hostname/identity"""
        try:
            if not hostname or not isinstance(hostname, str):
                return {
                    "status": "error",
                    "error": "hostname is required and must be a string"
                }

            # Basic Cisco hostname validation
            if len(hostname) > 63 or " " in hostname:
                return {
                    "status": "error",
                    "error": "invalid hostname format"
                }

            if logger:
                logger(f"Setting switch identity to '{hostname}'")

            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"hostname {hostname}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)

            # Save config
            self.save_config(logger)

            # Verify hostname
            verify = self.base.execute_command(
                "show running-config | include hostname",
                enable_mode=True
            )

            if hostname not in verify:
                raise Exception("hostname verification failed")

            return {
                "status": "success",
                "hostname": hostname,
                "message": "Switch identity updated successfully"
            }

        except Exception as e:
            if logger:
                logger(f"Error setting hostname: {str(e)}")

            return {
                "status": "error",
                "error": str(e)
            }
import re

class CiscoVlanDriver:
    def __init__(self, config):
        self.config = config
        self.base = None
    
    def get_vlans(self, logger=None):
        """Get all VLANs"""
        try:
            if logger:
                logger("Getting VLANs...")
            
            output = self.base.execute_command("show vlan brief", enable_mode=True)
            
            vlans = []
            lines = output.split('\n')
            
            for line in lines:
                if line.strip() and line[0].isdigit():
                    parts = line.split()
                    if len(parts) >= 2:
                        vlan_info = {
                            'vlan_id': parts[0],
                            'name': parts[1],
                            'status': 'active' if len(parts) > 2 and 'active' in parts[2].lower() else 'inactive',
                            'interfaces': parts[3:] if len(parts) > 3 else []
                        }
                        vlans.append(vlan_info)
            
            if logger:
                logger(f"Found {len(vlans)} VLANs")
            
            return {
                'status': 'success',
                'vlans': vlans
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting VLANs: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def create_vlan(self, vlan_id, name=None, logger=None):
        try:
            if logger:
                logger(f"Creating VLAN {vlan_id}...")

            self.base.execute_command("configure terminal", enable_mode=True)

            self.base.execute_command(f"vlan {vlan_id}", enable_mode=True)

            if name:
                self.base.execute_command(f"name {name}", enable_mode=True)

            self.base.execute_command("end", enable_mode=True)

            # Verifikasi Command
            verify = self.base.execute_command(
                f"show vlan id {vlan_id}",
                enable_mode=True
            )

            if "not found" in verify.lower():
                raise Exception("VLAN not created (verification failed)")

            if logger:
                logger(f"VLAN {vlan_id} successfully verified")

            return {
                'status': 'success',
                'message': f'VLAN {vlan_id} created',
                'vlan_id': vlan_id,
                'name': name or f'VLAN{vlan_id}'
            }

        except Exception as e:
            if logger:
                logger(f"Error creating VLAN: {str(e)}")

            return {
                'status': 'error',
                'error': str(e)
            }

    
    def delete_vlan(self, vlan_id, logger=None):
        try:
            if logger:
                logger(f"Deleting VLAN {vlan_id}...")

            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"no vlan {vlan_id}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)

            verify = self.base.execute_command(
                f"show vlan id {vlan_id}",
                enable_mode=True
            )

            if "not found" not in verify.lower():
                raise Exception("VLAN still exists after delete")

            self.base.execute_command("write memory", enable_mode=True)

            return {
                "status": "success",
                "message": f"VLAN {vlan_id} deleted"
            }

        except Exception as e:
            if logger:
                logger(f"Error deleting VLAN: {e}")
            return {"status": "error", "error": str(e)}

    def assign_vlan_access(self, interface_name, vlan_id, logger=None):
        try:
            if logger:
                logger(f"Assigning {interface_name} to VLAN {vlan_id}")

            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {interface_name}", enable_mode=True)
            self.base.execute_command("switchport mode access", enable_mode=True)
            self.base.execute_command(f"switchport access vlan {vlan_id}", enable_mode=True)
            self.base.execute_command("exit", enable_mode=True)
            self.base.execute_command("end",enable_mode=True)

            self.base.execute_command("write memory", enable_mode=True)

            return {
                "status": "success",
                "interface": interface_name,
                "vlan_id": vlan_id,
                "mode": "access"
            }

        except Exception as e:
            if logger:
                logger(f"Error assigning VLAN: {e}")
            return {"status": "error", "error": str(e)}

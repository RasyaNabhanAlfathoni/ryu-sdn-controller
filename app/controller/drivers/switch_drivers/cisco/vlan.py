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
        """Create VLAN"""
        try:
            if logger:
                logger(f"Creating VLAN {vlan_id}...")
            
            config_commands = [
                f"vlan {vlan_id}"
            ]
            
            if name:
                config_commands.append(f"name {name}")
            
            config_commands.append("exit")
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"VLAN {vlan_id} created")
            
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
        """Delete VLAN"""
        try:
            if logger:
                logger(f"Deleting VLAN {vlan_id}...")
            
            config_commands = [
                f"no vlan {vlan_id}"
            ]
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"VLAN {vlan_id} deleted")
            
            return {
                'status': 'success',
                'message': f'VLAN {vlan_id} deleted'
            }
            
        except Exception as e:
            if logger:
                logger(f"Error deleting VLAN: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def assign_vlan_access(self, interface_name, vlan_id, logger=None):
        """Assign VLAN access port"""
        try:
            if logger:
                logger(f"Assigning {interface_name} to VLAN {vlan_id} as access port...")
            
            config_commands = [
                f"interface {interface_name}",
                "switchport mode access",
                f"switchport access vlan {vlan_id}",
                "exit"
            ]
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"Interface {interface_name} assigned to VLAN {vlan_id}")
            
            return {
                'status': 'success',
                'message': f'Interface {interface_name} assigned to VLAN {vlan_id}',
                'interface': interface_name,
                'vlan_id': vlan_id,
                'mode': 'access'
            }
            
        except Exception as e:
            if logger:
                logger(f"Error assigning VLAN access: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
"""
Cisco Port Security Management
"""
import re

class CiscoSecurityDriver:
    def __init__(self, config):
        self.config = config
        self.base = None
    
    def set_base(self, base):
        """Set base SSH connection"""
        self.base = base
    
    def enable_port_security(self, interface, max_mac=1, violation='shutdown', logger=None):
        """Enable port security on interface"""
        try:
            if logger:
                logger(f"Enabling port security on {interface}...")
            
            config_commands = [
                f"interface {interface}",
                "switchport mode access",
                "switchport port-security",
                f"switchport port-security maximum {max_mac}",
                f"switchport port-security violation {violation}",
                "switchport port-security aging time 5",
                "switchport port-security aging type inactivity",
                "exit"
            ]
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"Port security enabled on {interface}")
            
            return {
                'status': 'success',
                'message': f'Port security enabled on {interface}',
                'interface': interface,
                'max_mac': max_mac,
                'violation_action': violation
            }
            
        except Exception as e:
            if logger:
                logger(f"Error enabling port security: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def disable_port_security(self, interface, logger=None):
        """Disable port security on interface"""
        try:
            if logger:
                logger(f"Disabling port security on {interface}...")
            
            config_commands = [
                f"interface {interface}",
                "no switchport port-security",
                "exit"
            ]
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"Port security disabled on {interface}")
            
            return {
                'status': 'success',
                'message': f'Port security disabled on {interface}',
                'interface': interface
            }
            
        except Exception as e:
            if logger:
                logger(f"Error disabling port security: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def enable_sticky_mac(self, interface, logger=None):
        """Enable sticky MAC learning on interface"""
        try:
            if logger:
                logger(f"Enabling sticky MAC on {interface}...")
            
            config_commands = [
                f"interface {interface}",
                "switchport port-security mac-address sticky",
                "exit"
            ]
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"Sticky MAC enabled on {interface}")
            
            return {
                'status': 'success',
                'message': f'Sticky MAC enabled on {interface}',
                'interface': interface
            }
            
        except Exception as e:
            if logger:
                logger(f"Error enabling sticky MAC: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def add_static_mac(self, interface, mac_address, vlan=1, logger=None):
        """Add static MAC address to port security"""
        try:
            if logger:
                logger(f"Adding static MAC {mac_address} to {interface}...")
            
            # Format MAC address
            mac_clean = mac_address.upper().replace(':', '').replace('.', '').replace('-', '')
            if len(mac_clean) == 12:
                mac_formatted = '.'.join([mac_clean[i:i+4] for i in range(0, 12, 4)])
            else:
                mac_formatted = mac_address
            
            config_commands = [
                f"interface {interface}",
                f"switchport port-security mac-address {mac_formatted} vlan {vlan}",
                "exit"
            ]
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"Static MAC {mac_address} added to {interface}")
            
            return {
                'status': 'success',
                'message': f'Static MAC {mac_address} added to {interface}',
                'interface': interface,
                'mac_address': mac_address,
                'vlan': vlan
            }
            
        except Exception as e:
            if logger:
                logger(f"Error adding static MAC: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_port_security_status(self, interface=None, logger=None):
        """Get port security status"""
        try:
            if logger:
                logger(f"Getting port security status for {interface or 'all'}...")
            
            if interface:
                cmd = f"show port-security interface {interface}"
            else:
                cmd = "show port-security"
            
            output = self.base.execute_command(cmd, enable_mode=True)
            
            status = self._parse_port_security(output)
            
            if logger:
                logger(f"Port security status collected")
            
            return {
                'status': 'success',
                'port_security': status
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting port security status: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _parse_port_security(self, output):
        """Parse show port-security output"""
        status = {
            'enabled': False,
            'interfaces': []
        }
        
        lines = output.split('\n')
        current_interface = None
        
        for line in lines:
            line = line.strip()
            
            if 'Port Security' in line and 'Enabled' in line:
                status['enabled'] = True
            
            elif line.startswith('Gi') or line.startswith('Fa'):
                if current_interface:
                    status['interfaces'].append(current_interface)
                
                parts = line.split()
                if len(parts) >= 2:
                    current_interface = {
                        'interface': parts[0],
                        'status': parts[1] if len(parts) > 1 else 'unknown'
                    }
            
            elif current_interface and ':' in line:
                key_val = line.split(':', 1)
                if len(key_val) == 2:
                    key = key_val[0].strip().lower().replace(' ', '_')
                    value = key_val[1].strip()
                    current_interface[key] = value
        
        if current_interface:
            status['interfaces'].append(current_interface)
        
        return status
    
    def clear_port_security(self, interface, logger=None):
        """Clear port security violation on interface"""
        try:
            if logger:
                logger(f"Clearing port security on {interface}...")
            
            # First shut and no shut
            config_commands = [
                f"interface {interface}",
                "shutdown",
                "no shutdown",
                "exit"
            ]
            
            result = self.base.configure_terminal(config_commands)
            
            # Clear port security counters
            clear_cmd = f"clear port-security sticky interface {interface}"
            clear_output = self.base.execute_command(clear_cmd, enable_mode=True)
            
            if logger:
                logger(f"Port security cleared on {interface}")
            
            return {
                'status': 'success',
                'message': f'Port security cleared on {interface}',
                'interface': interface
            }
            
        except Exception as e:
            if logger:
                logger(f"Error clearing port security: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
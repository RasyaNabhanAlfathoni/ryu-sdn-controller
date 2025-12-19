"""
Cisco Spanning Tree Protocol (STP) Management
"""
import re

class CiscoSTPDriver:
    def __init__(self, config):
        self.config = config
        self.base = None
    
    def set_base(self, base):
        """Set base SSH connection"""
        self.base = base
    
    def get_stp_info(self, logger=None):
        """Get STP information"""
        try:
            if logger:
                logger("Getting STP information...")
            
            # Get STP status
            cmd = "show spanning-tree"
            output = self.base.execute_command(cmd, enable_mode=True)
            
            # Get STP summary
            cmd_summary = "show spanning-tree summary"
            output_summary = self.base.execute_command(cmd_summary, enable_mode=True)
            
            # Parse outputs
            stp_info = self._parse_stp_output(output)
            stp_summary = self._parse_stp_summary(output_summary)
            
            if logger:
                logger("STP information collected")
            
            return {
                'status': 'success',
                'stp_info': stp_info,
                'stp_summary': stp_summary
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting STP info: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _parse_stp_output(self, output):
        """Parse show spanning-tree output"""
        info = {
            'bridge_id': '',
            'root_bridge': '',
            'root_cost': '',
            'root_port': '',
            'hello_time': '',
            'max_age': '',
            'forward_delay': ''
        }
        
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            
            # Bridge ID
            if 'Bridge ID' in line:
                match = re.search(r'Bridge ID\s+(\S+)', line)
                if match:
                    info['bridge_id'] = match.group(1)
            
            # Root Bridge
            elif 'Root ID' in line:
                match = re.search(r'Root ID\s+(\S+)', line)
                if match:
                    info['root_bridge'] = match.group(1)
            
            # Cost to Root
            elif 'Cost' in line:
                match = re.search(r'Cost\s+(\d+)', line)
                if match:
                    info['root_cost'] = match.group(1)
            
            # Root Port
            elif 'Root Port' in line:
                match = re.search(r'Root Port\s+(\S+)', line)
                if match:
                    info['root_port'] = match.group(1)
            
            # Timers
            elif 'Hello' in line:
                match = re.search(r'Hello\s+(\d+)', line)
                if match:
                    info['hello_time'] = match.group(1)
            
            elif 'Max Age' in line:
                match = re.search(r'Max Age\s+(\d+)', line)
                if match:
                    info['max_age'] = match.group(1)
            
            elif 'Forward Delay' in line:
                match = re.search(r'Forward Delay\s+(\d+)', line)
                if match:
                    info['forward_delay'] = match.group(1)
        
        return info
    
    def _parse_stp_summary(self, output):
        """Parse show spanning-tree summary"""
        summary = {
            'stp_enabled': False,
            'mode': 'Unknown',
            'vlans': 0
        }
        
        lines = output.split('\n')
        for line in lines:
            line = line.strip().lower()
            
            if 'spanning tree enabled' in line:
                summary['stp_enabled'] = 'yes' in line or 'true' in line
            
            elif 'mode' in line:
                if 'rapid-pvst' in line:
                    summary['mode'] = 'Rapid-PVST'
                elif 'pvst' in line:
                    summary['mode'] = 'PVST'
                elif 'mst' in line:
                    summary['mode'] = 'MST'
            
            elif 'vlans' in line:
                match = re.search(r'vlans?\s+(\d+)', line)
                if match:
                    summary['vlans'] = int(match.group(1))
        
        return summary
    
    def enable_stp(self, logger=None):
        """Enable STP globally"""
        try:
            if logger:
                logger("Enabling STP...")
            
            config_commands = [
                "spanning-tree mode rapid-pvst",
                "spanning-tree extend system-id"
            ]
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger("STP enabled successfully")
            
            return {
                'status': 'success',
                'message': 'STP enabled with Rapid-PVST mode'
            }
            
        except Exception as e:
            if logger:
                logger(f"Error enabling STP: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def disable_stp(self, logger=None):
        """Disable STP globally"""
        try:
            if logger:
                logger("Disabling STP...")
            
            config_commands = [
                "no spanning-tree mode",
                "spanning-tree portfast bpduguard default"
            ]
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger("STP disabled")
            
            return {
                'status': 'success',
                'message': 'STP disabled'
            }
            
        except Exception as e:
            if logger:
                logger(f"Error disabling STP: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def set_bridge_priority(self, priority, vlan=None, logger=None):
        """Set bridge priority"""
        try:
            if logger:
                logger(f"Setting bridge priority to {priority}...")
            
            config_commands = []
            
            if vlan:
                config_commands.append(f"spanning-tree vlan {vlan} priority {priority}")
            else:
                config_commands.append(f"spanning-tree priority {priority}")
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"Bridge priority set to {priority}")
            
            return {
                'status': 'success',
                'message': f'Bridge priority set to {priority}'
            }
            
        except Exception as e:
            if logger:
                logger(f"Error setting bridge priority: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def configure_portfast(self, interface=None, logger=None):
        """Configure PortFast on interface"""
        try:
            if logger:
                logger(f"Configuring PortFast on {interface or 'all'}...")
            
            config_commands = []
            
            if interface:
                config_commands.append(f"interface {interface}")
                config_commands.append("spanning-tree portfast")
                config_commands.append("exit")
            else:
                config_commands.append("spanning-tree portfast default")
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger("PortFast configured")
            
            return {
                'status': 'success',
                'message': 'PortFast configured'
            }
            
        except Exception as e:
            if logger:
                logger(f"Error configuring PortFast: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
"""
Cisco LLDP (Link Layer Discovery Protocol) Management via SSH
"""
import re

class CiscoLLDPDriver:
    """LLDP management via SSH"""
    
    def __init__(self, config):
        self.config = config
        self.base = None
    
    def set_base(self, base):
        """Set base SSH connection"""
        self.base = base
    
    def get_lldp_neighbors(self, logger=None):
        """Get LLDP neighbor information via SSH"""
        try:
            if logger:
                logger("Getting LLDP neighbors...")
            
            # Get LLDP neighbors
            cmd = "show lldp neighbors"
            output = self.base.execute_command(cmd, enable_mode=True)
            
            # Get detailed LLDP info
            cmd_detail = "show lldp neighbors detail"
            output_detail = self.base.execute_command(cmd_detail, enable_mode=True)
            
            neighbors = self._parse_lldp_neighbors(output, output_detail)
            
            if logger:
                logger(f"Retrieved {len(neighbors)} LLDP neighbors")
            
            return {
                'status': 'success',
                'neighbors': neighbors,
                'count': len(neighbors),
                'raw_output': output[:200]  # First 200 chars
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting LLDP neighbors: {str(e)}")
            
            # Fallback to simple show lldp neighbors
            try:
                cmd_simple = "show lldp neighbors"
                output_simple = self.base.execute_command(cmd_simple, enable_mode=True)
                neighbors_simple = self._parse_simple_lldp(output_simple)
                
                return {
                    'status': 'partial',
                    'neighbors': neighbors_simple,
                    'count': len(neighbors_simple),
                    'error': str(e)
                }
            except:
                return {
                    'status': 'error',
                    'error': str(e),
                    'neighbors': []
                }
    
    def _parse_lldp_neighbors(self, output, detail_output):
        """Parse LLDP neighbors from CLI output"""
        neighbors = []
        
        # First parse the summary table
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if 'Gi' in line or 'Fa' in line or 'Te' in line:
                parts = line.split()
                if len(parts) >= 4:
                    neighbor_info = {
                        'local_port': parts[0],
                        'neighbor_device': parts[1] if len(parts) > 1 else 'Unknown',
                        'neighbor_port': parts[2] if len(parts) > 2 else 'Unknown',
                        'ttl': parts[3] if len(parts) > 3 else 'Unknown'
                    }
                    neighbors.append(neighbor_info)
        
        # Parse detailed info to get more data
        if detail_output:
            self._enhance_with_detail(neighbors, detail_output)
        
        return neighbors
    
    def _parse_simple_lldp(self, output):
        """Simple parsing for basic LLDP output"""
        neighbors = []
        
        # Look for pattern: Local Intf | Port ID | System Name | etc.
        lines = output.split('\n')
        
        # Skip header lines
        for line in lines:
            if '----' in line:
                continue
            
            # Match interface lines
            if ('Gi' in line or 'Fa' in line or 'Te' in line) and len(line.strip()) > 10:
                parts = line.split()
                if len(parts) >= 4:
                    neighbor = {
                        'local_port': parts[0],
                        'neighbor_device': parts[1],
                        'neighbor_port': parts[2],
                        'ttl': parts[3] if len(parts) > 3 else 'N/A'
                    }
                    neighbors.append(neighbor)
        
        return neighbors
    
    def _enhance_with_detail(self, neighbors, detail_output):
        """Enhance neighbor info with detailed output"""
        current_neighbor = None
        detail_sections = detail_output.split('Local Intf: ')
        
        for section in detail_sections[1:]:  # Skip first empty section
            lines = section.split('\n')
            if not lines:
                continue
            
            local_intf = lines[0].strip()
            
            # Find this interface in neighbors list
            for neighbor in neighbors:
                if neighbor['local_port'] == local_intf:
                    for line in lines:
                        line = line.strip()
                        
                        # Parse chassis id
                        if 'Chassis id:' in line:
                            neighbor['chassis_id'] = line.split('Chassis id:')[-1].strip()
                        
                        # Parse system name
                        elif 'System Name:' in line:
                            neighbor['system_name'] = line.split('System Name:')[-1].strip()
                        
                        # Parse port description
                        elif 'Port Description:' in line:
                            neighbor['port_description'] = line.split('Port Description:')[-1].strip()
                        
                        # Parse system description
                        elif 'System Description:' in line:
                            neighbor['system_description'] = line.split('System Description:')[-1].strip()
                        
                        # Parse capabilities
                        elif 'System Capabilities:' in line:
                            caps = line.split('System Capabilities:')[-1].strip()
                            neighbor['capabilities'] = caps
                    
                    break
    
    def enable_lldp(self, interface=None, logger=None):
        """Enable LLDP globally or on specific interface via SSH"""
        try:
            if logger:
                if interface:
                    logger(f"Enabling LLDP on interface {interface}...")
                else:
                    logger("Enabling LLDP globally...")
            
            config_commands = []
            
            if interface:
                # Enable LLDP on specific interface
                config_commands.append(f"interface {interface}")
                config_commands.append("lldp transmit")
                config_commands.append("lldp receive")
                config_commands.append("exit")
            else:
                # Enable LLDP globally
                config_commands.append("lldp run")
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                if interface:
                    logger(f"Enabled LLDP on interface {interface}")
                else:
                    logger("Enabled LLDP globally")
            
            return {
                'status': 'success',
                'message': f'LLDP enabled{" on " + interface if interface else " globally"}',
                'commands': config_commands
            }
            
        except Exception as e:
            if logger:
                logger(f"Error enabling LLDP: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def disable_lldp(self, interface=None, logger=None):
        """Disable LLDP via SSH"""
        try:
            if logger:
                if interface:
                    logger(f"Disabling LLDP on interface {interface}...")
                else:
                    logger("Disabling LLDP globally...")
            
            config_commands = []
            
            if interface:
                # Disable LLDP on specific interface
                config_commands.append(f"interface {interface}")
                config_commands.append("no lldp transmit")
                config_commands.append("no lldp receive")
                config_commands.append("exit")
            else:
                # Disable LLDP globally
                config_commands.append("no lldp run")
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                if interface:
                    logger(f"Disabled LLDP on interface {interface}")
                else:
                    logger("Disabled LLDP globally")
            
            return {
                'status': 'success',
                'message': f'LLDP disabled{" on " + interface if interface else " globally"}',
                'commands': config_commands
            }
            
        except Exception as e:
            if logger:
                logger(f"Error disabling LLDP: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_lldp_status(self, logger=None):
        """Get LLDP status via SSH"""
        try:
            if logger:
                logger("Getting LLDP status...")
            
            # Check if LLDP is running globally
            cmd = "show lldp"
            output = self.base.execute_command(cmd, enable_mode=True)
            
            # Parse status
            enabled = False
            lines = output.split('\n')
            
            for line in lines:
                if 'Active' in line:
                    enabled = True
                    break
            
            # Get interface-specific status
            interface_status = self._get_interface_lldp_status()
            
            if logger:
                logger(f"LLDP status: {'Enabled' if enabled else 'Disabled'}")
            
            return {
                'status': 'success',
                'enabled': enabled,
                'interface_status': interface_status,
                'global_status': 'enabled' if enabled else 'disabled'
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting LLDP status: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e),
                'enabled': False
            }
    
    def _get_interface_lldp_status(self):
        """Get LLDP status per interface"""
        try:
            cmd = "show lldp interface"
            output = self.base.execute_command(cmd, enable_mode=True)
            
            interfaces = []
            lines = output.split('\n')
            
            for line in lines:
                if 'Gi' in line or 'Fa' in line or 'Te' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        intf_info = {
                            'interface': parts[0],
                            'tx_enabled': parts[1].lower() == 'enabled',
                            'rx_enabled': parts[2].lower() == 'enabled',
                            'tx_state': parts[3] if len(parts) > 3 else 'unknown'
                        }
                        interfaces.append(intf_info)
            
            return interfaces
            
        except:
            return []
    
    def get_lldp_statistics(self, interface=None, logger=None):
        """Get LLDP statistics via SSH"""
        try:
            if logger:
                logger(f"Getting LLDP statistics for {interface or 'all interfaces'}...")
            
            if interface:
                cmd = f"show lldp traffic {interface}"
            else:
                cmd = "show lldp traffic"
            
            output = self.base.execute_command(cmd, enable_mode=True)
            
            stats = self._parse_lldp_statistics(output)
            
            if logger:
                logger(f"LLDP statistics retrieved")
            
            return {
                'status': 'success',
                'statistics': stats,
                'interface': interface or 'global'
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting LLDP statistics: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _parse_lldp_statistics(self, output):
        """Parse LLDP statistics from CLI output"""
        stats = {
            'frames_transmitted': 0,
            'frames_received': 0,
            'frames_received_in_error': 0,
            'frames_discarded': 0,
            'tlv_discarded': 0,
            'entries_aged_out': 0
        }
        
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip().lower()
            
            if 'total frames transmitted' in line:
                match = re.search(r'(\d+)', line)
                if match:
                    stats['frames_transmitted'] = int(match.group(1))
            
            elif 'total frames received' in line:
                match = re.search(r'(\d+)', line)
                if match:
                    stats['frames_received'] = int(match.group(1))
            
            elif 'total frames received in error' in line:
                match = re.search(r'(\d+)', line)
                if match:
                    stats['frames_received_in_error'] = int(match.group(1))
            
            elif 'total frames discarded' in line:
                match = re.search(r'(\d+)', line)
                if match:
                    stats['frames_discarded'] = int(match.group(1))
            
            elif 'total tlvs discarded' in line:
                match = re.search(r'(\d+)', line)
                if match:
                    stats['tlv_discarded'] = int(match.group(1))
            
            elif 'total entries aged out' in line:
                match = re.search(r'(\d+)', line)
                if match:
                    stats['entries_aged_out'] = int(match.group(1))
        
        return stats
    
    def clear_lldp_statistics(self, interface=None, logger=None):
        """Clear LLDP statistics via SSH"""
        try:
            if logger:
                logger(f"Clearing LLDP statistics for {interface or 'all interfaces'}...")
            
            if interface:
                cmd = f"clear lldp counters {interface}"
            else:
                cmd = "clear lldp counters"
            
            output = self.base.execute_command(cmd, enable_mode=True)
            
            if logger:
                logger(f"LLDP statistics cleared")
            
            return {
                'status': 'success',
                'message': f'LLDP statistics cleared{" for " + interface if interface else ""}',
                'command': cmd
            }
            
        except Exception as e:
            if logger:
                logger(f"Error clearing LLDP statistics: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
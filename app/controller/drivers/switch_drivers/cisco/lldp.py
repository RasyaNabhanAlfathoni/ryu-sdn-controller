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
        neighbors = []
        lines = output.splitlines()

        header_found = False

        for line in lines:
            line = line.rstrip()

            # Skip legend & empty
            if not line or line.startswith("Capability"):
                continue

            # Deteksi header tabel
            if "Device ID" in line and "Local Intf" in line:
                header_found = True
                continue

            if not header_found:
                continue

            # Parse tabel LLDP
            parts = re.split(r'\s{2,}', line)
            if len(parts) < 4:
                continue

            device_id = parts[0]
            local_intf = parts[1]
            hold_time = parts[2]
            capability = parts[3]

            neighbors.append({
                "local_port": local_intf,
                "neighbor_device": device_id,
                "neighbor_port": None,      # di summary memang tidak ada
                "ttl": hold_time,
                "capabilities": capability
            })

        # Enrich dari detail (opsional)
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
            
            if interface:
                # Enable LLDP on specific interface
                self.base.execute_command("configure terminal", enable_mode=True)
                self.base.execute_command(f"interface {interface}", enable_mode=True)
                self.base.execute_command("lldp transmit", enable_mode=True)
                self.base.execute_command("lldp receive", enable_mode=True)
                self.base.execute_command("exit", enable_mode=True)
                self.base.execute_command("end", enable_mode=True)
            else:
                # Enable LLDP globally
                self.base.execute_command("configure terminal", enable_mode=True)
                self.base.execute_command("lldp run", enable_mode=True)
                self.base.execute_command("exit", enable_mode=True)
                self.base.execute_command("end", enable_mode=True)
            
            if logger:
                if interface:
                    logger(f"Enabled LLDP on interface {interface}")
                else:
                    logger("Enabled LLDP globally")

            # Save configuration
            save_result = self.base.save_configuration()
            
            return {
                'status': 'success',
                'message': f'LLDP enabled{" on " + interface if interface else " globally"}',
                'result': save_result
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
            
            if interface:
                # Enable LLDP on specific interface
                self.base.execute_command("configure terminal", enable_mode=True)
                self.base.execute_command(f"interface {interface}", enable_mode=True)
                self.base.execute_command("no lldp transmit", enable_mode=True)
                self.base.execute_command("no lldp receive", enable_mode=True)
                self.base.execute_command("exit", enable_mode=True)
                self.base.execute_command("end", enable_mode=True)
            else:
                # Enable LLDP globally
                self.base.execute_command("configure terminal", enable_mode=True)
                self.base.execute_command("no lldp run", enable_mode=True)
                self.base.execute_command("exit", enable_mode=True)
                self.base.execute_command("end", enable_mode=True)
            
            if logger:
                if interface:
                    logger(f"Enabled LLDP on interface {interface}")
                else:
                    logger("Enabled LLDP globally")

            # Save configuration
            save_result = self.base.save_configuration()
            
            if logger:
                if interface:
                    logger(f"Disabled LLDP on interface {interface}")
                else:
                    logger("Disabled LLDP globally")
            
            return {
                'status': 'success',
                'message': f'LLDP disabled{" on " + interface if interface else " globally"}',
                'result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error disabling LLDP: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_lldp_status(self, logger=None):
        """Get global & per-interface LLDP status"""
        try:
            if logger:
                logger("Getting LLDP global status...")

            try:
                global_enabled = False
                tx_interval = None
                holdtime = None
                
                output = self.base.execute_command("show lldp", enable_mode=True)

                for line in output.splitlines():
                    l = line.lower().strip()

                    # Explicit status
                    if "Status:" in l:
                        if "ACTIVE" in l:
                            global_enabled = True
                        elif "INACTIVE" in l:
                            global_enabled = False

                    # Timer-based inference
                    if "advertisements are sent every" in l:
                        global_enabled = True
                        match = re.search(r'(\d+)', l)
                        if match:
                            tx_interval = int(match.group(1))

                    if "hold time" in l:
                        global_enabled = True
                        match = re.search(r'(\d+)', l)
                        if match:
                            holdtime = int(match.group(1))

                    # Legacy IOS
                    if "lldp is enabled" in l:
                        global_enabled = True

                    if "lldp is not enabled" in l:
                        global_enabled = False

            except Exception:
                pass

            interfaces = self._get_interface_lldp_status()

            return {
                "status": "success",
                "enabled": global_enabled,
                "tx_interval": tx_interval,
                "holdtime": holdtime,
                "interfaces": interfaces
            }

        except Exception as e:
            if logger:
                logger(f"Error getting LLDP status: {str(e)}")

            return {
                "status": "error",
                "error": str(e)
            }
    
    def _get_interface_lldp_status(self):
        """Universal Cisco LLDP interface parser (IOS / IOSv / PNET / CML)"""
        try:
            output = self.base.execute_command("show lldp interface", enable_mode=True)

            if not output.strip():
                return [{
                    "info": "Interface-level LLDP status not available on this IOS image"
                }]

            if re.search(r'^\S+:\s*$', output, re.MULTILINE):
                return self._parse_lldp_interface_block(output)

            if "Interface" in output:
                return self._parse_lldp_interface_table(output)

            return [{
                "info": "Unknown LLDP interface output format",
                "raw": output[:200]
            }]

        except Exception as e:
            return [{
                "error": str(e)
            }]

    def _parse_lldp_interface_block(self, output):
        interfaces = []
        current = None

        for line in output.splitlines():
            line = line.rstrip()

            # Interface header (Ethernet0/0:)
            if re.match(r'^\S+:\s*$', line):
                if current:
                    interfaces.append(current)

                current = {
                    "interface": line.replace(":", ""),
                    "tx": None,
                    "rx": None,
                    "tx_state": None,
                    "rx_state": None
                }

            elif current:
                if "Tx:" in line:
                    current["tx"] = "enabled" in line.lower()

                elif "Rx:" in line:
                    current["rx"] = "enabled" in line.lower()

                elif "Tx state:" in line:
                    current["tx_state"] = line.split("Tx state:")[-1].strip()

                elif "Rx state:" in line:
                    current["rx_state"] = line.split("Rx state:")[-1].strip()

        if current:
            interfaces.append(current)

        return interfaces

    def _parse_lldp_interface_table(self, output):
        interfaces = []
        header_found = False

        for line in output.splitlines():
            line = line.strip()

            if not line:
                continue

            if line.startswith("Interface"):
                header_found = True
                continue

            if not header_found:
                continue

            parts = re.split(r'\s+', line)
            if len(parts) < 4:
                continue

            interfaces.append({
                "interface": parts[0],
                "tx": parts[1].upper() == "YES",
                "rx": parts[2].upper() == "YES",
                "state": parts[3]
            })

        return interfaces

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
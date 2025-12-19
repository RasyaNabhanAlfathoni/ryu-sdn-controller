import re
from drivers.snmp_file_manager import SNMPFileManager

class CiscoSnmpDriver:
    """
    SNMP Configuration & Community Management for Cisco via SSH
    """
    
    def __init__(self, config):
        self.config = config
        self.base = None
    
    def set_base(self, base):
        """Set base SSH connection"""
        self.base = base
    
    # =====================================================
    # SNMP GLOBAL CONFIG
    # =====================================================
    def get_snmp_info(self, p=None, logger=print):
        """Get SNMP configuration information via SSH"""
        try:
            if logger:
                logger("Getting SNMP configuration...")
            
            # Get SNMP running config
            cmd = "show running-config | include snmp-server"
            output = self.base.execute_command(cmd, enable_mode=True)
            
            snmp_info = self._parse_snmp_config(output)
            
            if logger:
                logger(f"SNMP config retrieved: Enabled={snmp_info.get('enabled', False)}")
            
            return {
                'status': 'success',
                'snmp_config': snmp_info,
                'raw_config': output[:500]  # First 500 chars
            }
            
        except Exception as e:
            if logger:
                logger(f"Get SNMP config failed: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e),
                'snmp_config': {}
            }
    
    def _parse_snmp_config(self, config_output):
        """Parse SNMP configuration from CLI output"""
        snmp_info = {
            'enabled': False,
            'contact': '',
            'location': '',
            'traps_enabled': False,
            'communities': [],
            'trap_hosts': []
        }
        
        lines = config_output.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Check for communities (indicates SNMP is enabled)
            if 'snmp-server community' in line:
                snmp_info['enabled'] = True
                
                # Parse community
                # Format: snmp-server community NAME RO/RW [ACL]
                match = re.search(r'snmp-server community (\S+) (\S+)(?: (\S+))?', line)
                if match:
                    community = {
                        'name': match.group(1),
                        'access': match.group(2).upper(),
                        'acl': match.group(3) if match.group(3) else ''
                    }
                    snmp_info['communities'].append(community)
            
            # Parse contact
            elif 'snmp-server contact' in line:
                match = re.search(r'snmp-server contact (.+)$', line)
                if match:
                    snmp_info['contact'] = match.group(1).strip()
            
            # Parse location
            elif 'snmp-server location' in line:
                match = re.search(r'snmp-server location (.+)$', line)
                if match:
                    snmp_info['location'] = match.group(1).strip()
            
            # Check if traps enabled
            elif 'snmp-server enable traps' in line:
                snmp_info['traps_enabled'] = True
            
            # Parse trap hosts
            elif 'snmp-server host' in line:
                # Format: snmp-server host IP COMMUNITY [version 2c]
                match = re.search(r'snmp-server host (\S+) (\S+)', line)
                if match:
                    host_info = {
                        'ip': match.group(1),
                        'community': match.group(2)
                    }
                    snmp_info['trap_hosts'].append(host_info)
        
        return snmp_info
    
    def configure_snmp(self, p, logger=print):
        """
        Configure SNMP settings via SSH.
        Example payload:
        {
            "enabled": true,
            "contact": "Network Admin",
            "location": "NOC Room",
            "community": "public",
            "community_access": "RO",
            "acl": "10",
            "traps_enabled": true,
            "trap_target": "192.168.1.100",
            "trap_community": "public"
        }
        """
        try:
            if logger:
                logger(f"Configuring SNMP with params: {p}")
            
            config_commands = []
            
            # Add contact if provided
            if p.get('contact'):
                config_commands.append(f"snmp-server contact {p['contact']}")
            
            # Add location if provided
            if p.get('location'):
                config_commands.append(f"snmp-server location {p['location']}")
            
            # Add community if provided
            if p.get('community'):
                community_name = p['community']
                community_access = p.get('community_access', 'RO')
                
                community_cmd = f"snmp-server community {community_name} {community_access}"
                
                # Add ACL if provided
                if p.get('acl'):
                    community_cmd += f" {p['acl']}"
                
                config_commands.append(community_cmd)
            
            # Enable traps if specified
            if p.get('traps_enabled'):
                config_commands.append("snmp-server enable traps")
            
            # Add trap target if provided
            if p.get('trap_target') and p.get('trap_community'):
                trap_cmd = f"snmp-server host {p['trap_target']} {p['trap_community']} version 2c"
                config_commands.append(trap_cmd)
            
            # Apply configuration
            if config_commands:
                result = self.base.configure_terminal(config_commands)
                
                # Auto-add to Prometheus SNMP targets if community provided
                if p.get('community') and p.get('add_to_prometheus', True):
                    try:
                        self._add_to_prometheus_targets(p, logger)
                    except Exception as e:
                        if logger:
                            logger(f"Warning: Could not add to Prometheus targets: {str(e)}")
                
                if logger:
                    logger(f"SNMP configuration updated: {len(config_commands)} commands applied")
                
                return {
                    'status': 'success',
                    'message': 'SNMP configured successfully',
                    'commands_applied': config_commands,
                    'config': p
                }
            else:
                return {
                    'status': 'warning',
                    'message': 'No SNMP configuration commands to apply'
                }
            
        except Exception as e:
            if logger:
                logger(f"Configure SNMP failed: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _add_to_prometheus_targets(self, p, logger):
        """Add switch to Prometheus SNMP targets"""
        # Get device info for hostname
        try:
            hostname_output = self.base.execute_command("show running-config | include hostname", enable_mode=True)
            hostname = 'Cisco-Switch'
            
            for line in hostname_output.split('\n'):
                if 'hostname' in line:
                    hostname = line.split('hostname')[-1].strip()
                    break
        except:
            hostname = 'Cisco-Switch'
        
        # Add to SNMP targets
        snmp_mgr = SNMPFileManager()
        snmp_mgr.add_device({
            "device_id": self.config.get('device_id', 'unknown'),
            "ip": self.config['ip'],
            "module": "cisco",
            "device_name": hostname,
            "community": p['community'],
            "location": p.get('location', 'Unknown')
        })
        
        if logger:
            logger(f"Added switch {hostname} to Prometheus SNMP targets")
    
    # =====================================================
    # SNMP COMMUNITY MANAGEMENT
    # =====================================================
    def list_communities(self, p=None, logger=print):
        """List all SNMP communities via SSH"""
        try:
            if logger:
                logger("Listing SNMP communities...")
            
            cmd = "show running-config | include snmp-server community"
            output = self.base.execute_command(cmd, enable_mode=True)
            
            communities = self._parse_communities(output)
            
            if logger:
                logger(f"Found {len(communities)} SNMP communities")
            
            return {
                'status': 'success',
                'communities': communities,
                'count': len(communities)
            }
            
        except Exception as e:
            if logger:
                logger(f"List communities failed: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e),
                'communities': []
            }
    
    def _parse_communities(self, config_output):
        """Parse SNMP communities from CLI output"""
        communities = []
        
        lines = config_output.split('\n')
        for line in lines:
            line = line.strip()
            
            # Format: snmp-server community NAME RO/RW [ACL]
            if 'snmp-server community' in line:
                match = re.search(r'snmp-server community (\S+) (\S+)(?: (\S+))?', line)
                if match:
                    community_info = {
                        'name': match.group(1),
                        'access': match.group(2).upper(),
                        'acl': match.group(3) if match.group(3) else ''
                    }
                    communities.append(community_info)
        
        return communities
    
    def add_community(self, p, logger=print):
        """
        Add SNMP community via SSH.
        Example payload:
        {
            "name": "monitoring",
            "access": "RO",  # or "RW"
            "acl": "10",
            "add_to_prometheus": true
        }
        """
        try:
            if "name" not in p:
                return {
                    'status': 'error',
                    'error': "Missing 'name' in payload"
                }
            
            if logger:
                logger(f"Adding SNMP community '{p['name']}'...")
            
            # Check if community already exists
            existing = self.list_communities(logger=logger)
            if existing.get('status') == 'success':
                for community in existing.get('communities', []):
                    if community['name'] == p['name']:
                        if logger:
                            logger(f"Community '{p['name']}' already exists")
                        
                        return {
                            'status': 'success',
                            'message': f"Community '{p['name']}' already exists",
                            'exists': True
                        }
            
            # Build community command
            access = p.get('access', 'RO')
            community_cmd = f"snmp-server community {p['name']} {access}"
            
            if p.get('acl'):
                community_cmd += f" {p['acl']}"
            
            # Apply configuration
            config_commands = [community_cmd]
            result = self.base.configure_terminal(config_commands)
            
            # Add to Prometheus if requested
            if p.get('add_to_prometheus', True):
                try:
                    self._add_community_to_prometheus(p, logger)
                except Exception as e:
                    if logger:
                        logger(f"Warning: Could not add to Prometheus: {str(e)}")
            
            if logger:
                logger(f"Added SNMP community: {p['name']}")
            
            return {
                'status': 'success',
                'message': f"SNMP community '{p['name']}' added",
                'community': p['name'],
                'command': community_cmd
            }
            
        except Exception as e:
            if logger:
                logger(f"Add community failed: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _add_community_to_prometheus(self, p, logger):
        """Add community to Prometheus SNMP targets"""
        # Get device info
        try:
            hostname_output = self.base.execute_command("show running-config | include hostname", enable_mode=True)
            hostname = 'Cisco-Switch'
            
            for line in hostname_output.split('\n'):
                if 'hostname' in line:
                    hostname = line.split('hostname')[-1].strip()
                    break
        except:
            hostname = 'Cisco-Switch'
        
        # Add to SNMP targets
        snmp_mgr = SNMPFileManager()
        snmp_mgr.add_device({
            "device_id": self.config.get('device_id', 'unknown'),
            "ip": self.config['ip'],
            "module": "cisco",
            "device_name": hostname,
            "community": p['name'],
            "location": p.get('location', 'Unknown')
        })
        
        if logger:
            logger(f"Added community '{p['name']}' to Prometheus SNMP targets")
    
    def edit_community(self, p, logger=print):
        """Edit SNMP community via SSH"""
        try:
            if "name" not in p:
                return {
                    'status': 'error',
                    'error': "Missing 'name' in payload"
                }
            
            if logger:
                logger(f"Editing SNMP community '{p['name']}'...")
            
            # First delete the old community
            delete_cmd = f"no snmp-server community {p['name']}"
            
            # Then add the new one
            add_payload = p.copy()
            result_add = self.add_community(add_payload, logger)
            
            if result_add.get('status') == 'success':
                # Apply delete command if adding was successful
                config_commands = [delete_cmd]
                self.base.configure_terminal(config_commands)
                
                if logger:
                    logger(f"Updated SNMP community '{p['name']}'")
            
            return result_add
            
        except Exception as e:
            if logger:
                logger(f"Edit community failed: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def delete_community(self, p, logger=print):
        """Delete SNMP community via SSH"""
        try:
            if "name" not in p:
                return {
                    'status': 'error',
                    'error': "Missing 'name' in payload"
                }
            
            if logger:
                logger(f"Deleting SNMP community '{p['name']}'...")
            
            # Delete community command
            delete_cmd = f"no snmp-server community {p['name']}"
            config_commands = [delete_cmd]
            
            result = self.base.configure_terminal(config_commands)
            
            # Also remove from Prometheus if exists
            try:
                snmp_mgr = SNMPFileManager()
                snmp_mgr.delete_device(self.config.get('device_id', 'unknown'))
            except:
                pass  # Ignore if not in Prometheus
            
            if logger:
                logger(f"Deleted SNMP community '{p['name']}'")
            
            return {
                'status': 'success',
                'message': f"SNMP community '{p['name']}' deleted",
                'command': delete_cmd
            }
            
        except Exception as e:
            if logger:
                logger(f"Delete community failed: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    # =====================================================
    # SNMP ENABLE / DISABLE
    # =====================================================
    def enable_snmp(self, p=None, logger=print):
        """Enable SNMP with default community via SSH"""
        try:
            if logger:
                logger("Enabling SNMP with default community...")
            
            payload = {
                'community': 'public',
                'access': 'RO',
                'add_to_prometheus': True
            }
            
            if p:
                payload.update(p)
            
            result = self.add_community(payload, logger)
            
            if result.get('status') == 'success':
                # Also enable traps by default
                try:
                    trap_commands = ["snmp-server enable traps"]
                    self.base.configure_terminal(trap_commands)
                except:
                    pass  # Ignore if traps not supported
            
            if logger:
                logger("SNMP enabled with default community")
            
            return result
            
        except Exception as e:
            if logger:
                logger(f"Enable SNMP failed: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def disable_snmp(self, p=None, logger=print):
        """Disable SNMP by removing all communities via SSH"""
        try:
            if logger:
                logger("Disabling SNMP (removing all communities)...")
            
            # Get all communities
            communities = self.list_communities(logger=logger)
            
            if communities.get('status') != 'success':
                return {
                    'status': 'success',
                    'message': 'SNMP already disabled or no communities found'
                }
            
            # Delete all communities
            delete_commands = []
            for community in communities.get('communities', []):
                delete_commands.append(f"no snmp-server community {community['name']}")
            
            if delete_commands:
                result = self.base.configure_terminal(delete_commands)
            
            # Remove from Prometheus
            try:
                snmp_mgr = SNMPFileManager()
                snmp_mgr.delete_device(self.config.get('device_id', 'unknown'))
            except:
                pass
            
            if logger:
                logger(f"SNMP disabled - {len(delete_commands)} communities removed")
            
            return {
                'status': 'success',
                'message': 'SNMP disabled successfully',
                'communities_removed': len(communities.get('communities', []))
            }
            
        except Exception as e:
            if logger:
                logger(f"Disable SNMP failed: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def test_snmp_connection(self, community='public', logger=print):
        """Test SNMP connectivity"""
        try:
            if logger:
                logger(f"Testing SNMP connectivity with community '{community}'...")
            
            # Try to get system info via SNMP (simulated via CLI)
            # In real implementation, use SNMP library
            cmd = f"show snmp community | include {community}"
            output = self.base.execute_command(cmd, enable_mode=True)
            
            if community in output:
                return {
                    'status': 'success',
                    'message': f'SNMP community "{community}" is active',
                    'accessible': True
                }
            else:
                return {
                    'status': 'warning',
                    'message': f'SNMP community "{community}" not found',
                    'accessible': False
                }
            
        except Exception as e:
            if logger:
                logger(f"Test SNMP connection failed: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e),
                'accessible': False
            }
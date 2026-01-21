import re
import logging
import json

class CiscoLoggingManagement:
    def __init__(self, config):
        self.config = config
        self.base = None
        self.logger = logging.getLogger(__name__)
    
    def set_base(self, base):
        """Set base SSH connection"""
        self.base = base

    def detect_management_interface(self, logger=None):
        """Detect management interface automatically"""
        try:
            if logger:
                logger("Detecting management interface...")
            
            # Cek IP interface brief untuk interface dengan IP yang sama dengan device
            ip_brief = self.base.execute_command("show ip interface brief", enable_mode=True)
            
            management_ip = None
            mgmt_interface = None
            
            # Dapatkan IP management dari konfigurasi atau hostname
            running_config = self.base.execute_command("show running-config", enable_mode=True)
            
            # Cari interface dengan IP address
            interface_pattern = r'interface\s+(\S+)\s*\n(?:[ \t].*\n)*[ \t]*ip\s+address\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)'
            interfaces = re.findall(interface_pattern, running_config, re.IGNORECASE)
            
            for intf, ip, mask in interfaces:
                if ip:  # Jika ada IP
                    mgmt_interface = intf
                    management_ip = ip
                    if logger:
                        logger(f"Found interface {intf} with IP {ip}")
                    break
            
            # Kalau tidak ditemukan, cari VLAN interface
            if not mgmt_interface:
                vlan_pattern = r'interface\s+(Vlan\d+)\s*\n(?:[ \t].*\n)*[ \t]*ip\s+address\s+'
                vlan_match = re.search(vlan_pattern, running_config, re.IGNORECASE)
                if vlan_match:
                    mgmt_interface = vlan_match.group(1)
                    if logger:
                        logger(f"Found VLAN interface {mgmt_interface}")
            
            # Fallback ke interface yang terhubung
            if not mgmt_interface:
                int_status = self.base.execute_command("show interface status", enable_mode=True)
                lines = int_status.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line or 'Port' in line:
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 4:
                        interface = parts[0]
                        status = parts[2].lower() if len(parts) > 3 else ''
                        
                        # Cari interface fisik yang connected
                        if (status == 'connected' and 
                            any(x in interface.lower() for x in ['ethernet', 'fast', 'gigabit', 'ten'])):
                            mgmt_interface = interface
                            if logger:
                                logger(f"Using connected interface {interface} as management")
                            break
            
            return {
                'status': 'success',
                'interface': mgmt_interface,
                'ip_address': management_ip,
                'detected': True if mgmt_interface else False
            }
            
        except Exception as e:
            error_msg = f"Error detecting management interface: {str(e)}"
            if logger:
                logger(error_msg)
            self.logger.error(error_msg)
            
            return {
                'status': 'error',
                'error': str(e),
                'interface': None
            }
    
    def get_logging_status(self, logger=None):
        """Get current logging configuration"""
        try:
            if logger:
                logger("Fetching logging configuration...")
            
            # Get logging configuration
            output = self.base.execute_command("show logging", enable_mode=True)
            
            # Get syslog servers if configured
            syslog_output = self.base.execute_command("show running-config | include logging", enable_mode=True)
            
            parsed_config = self._parse_logging_output(output, syslog_output)
            
            if logger:
                logger(f"Logging status: {parsed_config.get('status', 'unknown')}")
            
            return {
                'status': 'success',
                'configuration': parsed_config
            }
            
        except Exception as e:
            error_msg = f"Error fetching logging status: {str(e)}"
            if logger:
                logger(error_msg)
            self.logger.error(error_msg)
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def configure_syslog(self, syslog_server, facility='local7', severity='informational', port=1511, 
                         protocol='udp', logger=None):
        """Configure syslog server with port support"""
        try:
            if logger:
                logger(f"Configuring syslog to {syslog_server}:{port}/{protocol}")

            detection = self.detect_management_interface(logger)
            if detection['status'] == 'success' and detection['interface']:
                source_interface = detection['interface']
                if logger:
                    logger(f"Auto-detected management interface: {source_interface}")
            else:
                if logger:
                    logger("Warning: Could not auto-detect management interface") 

            severity_levels = {
                'emergencies': 0,
                'alerts': 1,
                'critical': 2,
                'errors': 3,
                'warnings': 4,
                'notifications': 5,
                'informational': 6,
                'debugging': 7
            }

            if severity.lower() not in severity_levels:
                raise ValueError("Invalid severity level")

            severity_num = severity_levels[severity.lower()]

            self.base.execute_command("configure terminal", enable_mode=True)

            if port != 514:
                self.base.execute_command(
                    f"logging host {syslog_server} transport {protocol} port {port}",
                    enable_mode=True
                )
            else:
                self.base.execute_command(f"logging host {syslog_server}", enable_mode=True)

            if source_interface:
                self.base.execute_command(f"logging source-interface {source_interface}", enable_mode=True)

            self.base.execute_command(f"logging trap {severity_num}", enable_mode=True)
            self.base.execute_command(f"logging facility {facility}", enable_mode=True)
            self.base.execute_command("logging on", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)

            self.base.execute_command("write memory", enable_mode=True)

            return {
                'status': 'success',
                'syslog_server': syslog_server,
                'port': port,
                'protocol': protocol,
                'severity': severity
            }

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def enable_syslog(self, logger=None):
        """Enable syslog globally (no target change)"""
        try:
            if logger:
                logger("Enabling syslog service")

            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command("logging on", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            self.base.execute_command("write memory", enable_mode=True)

            return {
                "status": "success",
                "enabled": True
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def disable_syslog(self, logger=None):
        """Disable syslog"""
        try:
            if logger:
                logger("Disabling syslog...")
            
            # Get current syslog servers
            output = self.base.execute_command("show running-config | include logging host", enable_mode=True)
            
            servers = []
            for line in output.split('\n'):
                if 'logging host' in line:
                    server = line.split('logging host')[-1].strip()
                    servers.append(server)
            
            # Remove all syslog servers
            self.base.execute_command("configure terminal", enable_mode=True)
            for server in servers:
                self.base.execute_command(f"no logging host {server}", enable_mode=True)
            self.base.execute_command("no logging on", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            self.base.execute_command("write memory", enable_mode=True)
            
            if logger:
                logger("Syslog disabled successfully")
            
            return {
                'status': 'success',
                'message': "Syslog disabled",
                'removed_servers': servers
            }
            
        except Exception as e:
            error_msg = f"Error disabling syslog: {str(e)}"
            if logger:
                logger(error_msg)
            self.logger.error(error_msg)
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def set_logging_severity(self, severity, logger=None):
        """Set logging severity level"""
        try:
            if logger:
                logger(f"Setting logging severity to {severity}")
            
            severity_mapping = {
                'emergencies': 0,
                'alerts': 1,
                'critical': 2,
                'errors': 3,
                'warnings': 4,
                'notifications': 5,
                'informational': 6,
                'debugging': 7
            }
            
            if severity.lower() not in severity_mapping:
                raise ValueError(f"Invalid severity. Valid options: {list(severity_mapping.keys())}")
            
            severity_num = severity_mapping[severity.lower()]
            
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"logging trap {severity_num}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            self.base.execute_command("write memory", enable_mode=True)
            
            if logger:
                logger(f"Logging severity set to {severity} (level {severity_num})")
            
            return {
                'status': 'success',
                'message': f"Logging severity set to {severity}",
                'severity': severity,
                'severity_level': severity_num
            }
            
        except Exception as e:
            error_msg = f"Error setting logging severity: {str(e)}"
            if logger:
                logger(error_msg)
            self.logger.error(error_msg)
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _parse_logging_output(self, logging_output, syslog_output):
        """Parse show logging output"""
        config = {
            'status': 'unknown',
            'syslog_enabled': False,
            'console_logging': False,
            'buffer_logging': False,
            'syslog_servers': [],
            'buffer_size': 0,
            'messages_logged': 0
        }
        
        # Parse syslog servers
        for line in syslog_output.split('\n'):
            if 'logging host' in line:
                server = line.split('logging host')[-1].strip()
                config['syslog_servers'].append(server)
                config['syslog_enabled'] = True
        
        # Parse logging output
        lines = logging_output.split('\n')
        for line in lines:
            line = line.strip()
            
            if 'Syslog logging:' in line:
                config['status'] = line.split(':')[-1].strip().lower()
            
            elif 'Console logging:' in line:
                console_status = line.split(':')[-1].strip().lower()
                config['console_logging'] = console_status != 'disabled'
            
            elif 'Buffer logging:' in line:
                buffer_status = line.split(':')[-1].strip().lower()
                config['buffer_logging'] = buffer_status != 'disabled'
            
            elif 'Log Buffer (' in line:
                match = re.search(r'Log Buffer \((\d+) bytes\)', line)
                if match:
                    config['buffer_size'] = int(match.group(1))
            
            elif 'messages logged' in line.lower():
                match = re.search(r'(\d+) messages logged', line)
                if match:
                    config['messages_logged'] = int(match.group(1))
        
        return config
    
    def _parse_log_entries(self, log_output):
        """Parse log entries from output"""
        logs = []
        
        log_pattern = re.compile(
            r'(\w+\s+\d+\s+\d+:\d+:\d+\.\d+):\s+%(\w+)-(\d+)-(\w+):\s+(.+)'
        )
        
        lines = log_output.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            match = log_pattern.match(line)
            if match:
                timestamp, facility, code, severity, message = match.groups()
                
                logs.append({
                    'timestamp': timestamp,
                    'facility': facility,
                    'code': int(code),
                    'severity': severity,
                    'message': message,
                    'raw': line
                })
            else:
                # Handle continuation lines
                if logs:
                    logs[-1]['message'] += f" {line}"
        
        return logs
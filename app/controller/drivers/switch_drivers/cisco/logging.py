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
    
    def configure_syslog(self, syslog_server, facility='local7', severity='informational', port=514, protocol='udp', logger=None):
        """Configure syslog server with port support"""
        try:
            if logger:
                logger(f"Configuring syslog to {syslog_server}:{port}/{protocol}")

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
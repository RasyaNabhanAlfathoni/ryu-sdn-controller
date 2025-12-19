import re

class CiscoQoSDriver:
    def __init__(self, config):
        self.config = config
        self.base = None
    
    def set_base(self, base):
        """Set base SSH connection"""
        self.base = base
    
    def set_rate_limit(self, interface, rate_kbps, direction='both', logger=None):
        """Set rate limiting on interface"""
        try:
            if logger:
                logger(f"Setting rate limit on {interface} to {rate_kbps} kbps...")
            
            # Convert kbps to Mbps jika perlu
            rate_mbps = rate_kbps / 1000.0
            
            config_commands = [
                f"interface {interface}",
                "srr-queue bandwidth share 10 10 60 20",
                "srr-queue bandwidth shape 10 0 0 0",
                f"priority-queue out",
                f"shape average {int(rate_kbps)}",
                "exit"
            ]
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"Rate limit {rate_kbps} kbps set on {interface}")
            
            return {
                'status': 'success',
                'message': f'Rate limit {rate_kbps} kbps set on {interface}',
                'interface': interface,
                'rate_kbps': rate_kbps,
                'direction': direction
            }
            
        except Exception as e:
            if logger:
                logger(f"Error setting rate limit: {str(e)}")
            
            # Fallback ke police rate
            try:
                return self._set_police_rate(interface, rate_kbps, logger)
            except Exception as e2:
                return {
                    'status': 'error',
                    'error': f"Primary: {str(e)}, Fallback: {str(e2)}"
                }
    
    def _set_police_rate(self, interface, rate_kbps, logger):
        """Fallback method using police rate"""
        if logger:
            logger(f"Trying police rate method...")
        
        # Convert to bps untuk police command
        rate_bps = rate_kbps * 1000
        
        config_commands = [
            f"interface {interface}",
            f"service-policy input limit-{interface}",
            "exit",
            f"policy-map limit-{interface}",
            f"class class-default",
            f"police {rate_bps} conform-action transmit exceed-action drop",
            "exit",
            "exit"
        ]
        
        result = self.base.configure_terminal(config_commands)
        
        return {
            'status': 'success',
            'message': f'Rate limit {rate_kbps} kbps set using police method',
            'method': 'police'
        }
    
    def create_qos_policy(self, policy_name, class_maps, logger=None):
        """Create QoS policy map"""
        try:
            if logger:
                logger(f"Creating QoS policy {policy_name}...")
            
            config_commands = [
                f"policy-map {policy_name}"
            ]
            
            for class_name, bandwidth_percent in class_maps.items():
                config_commands.append(f"class {class_name}")
                config_commands.append(f"bandwidth percent {bandwidth_percent}")
                config_commands.append("exit")
            
            config_commands.append("exit")
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"QoS policy {policy_name} created")
            
            return {
                'status': 'success',
                'message': f'QoS policy {policy_name} created',
                'policy_name': policy_name,
                'class_maps': class_maps
            }
            
        except Exception as e:
            if logger:
                logger(f"Error creating QoS policy: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def apply_qos_policy(self, interface, policy_name, direction='input', logger=None):
        """Apply QoS policy to interface"""
        try:
            if logger:
                logger(f"Applying QoS policy {policy_name} to {interface}...")
            
            config_commands = [
                f"interface {interface}",
                f"service-policy {direction} {policy_name}",
                "exit"
            ]
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"QoS policy applied to {interface}")
            
            return {
                'status': 'success',
                'message': f'QoS policy {policy_name} applied to {interface}',
                'interface': interface,
                'policy': policy_name,
                'direction': direction
            }
            
        except Exception as e:
            if logger:
                logger(f"Error applying QoS policy: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_qos_status(self, logger=None):
        """Get QoS configuration status"""
        try:
            if logger:
                logger("Getting QoS status...")
            
            # Get policy maps
            cmd_policy = "show policy-map"
            output_policy = self.base.execute_command(cmd_policy, enable_mode=True)
            
            # Get interface QoS
            cmd_intf = "show policy-map interface"
            output_intf = self.base.execute_command(cmd_intf, enable_mode=True)
            
            policies = self._parse_policy_maps(output_policy)
            applied = self._parse_applied_policies(output_intf)
            
            if logger:
                logger(f"Found {len(policies)} QoS policies")
            
            return {
                'status': 'success',
                'policies': policies,
                'applied_policies': applied
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting QoS status: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _parse_policy_maps(self, output):
        """Parse show policy-map output"""
        policies = []
        current_policy = None
        
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            
            if line.startswith('Policy Map'):
                if current_policy:
                    policies.append(current_policy)
                
                policy_name = line.split('Policy Map')[-1].strip().replace('"', '')
                current_policy = {
                    'name': policy_name,
                    'classes': []
                }
            
            elif line.startswith('Class') and current_policy:
                class_name = line.split('Class')[-1].strip().replace('"', '')
                current_policy['classes'].append(class_name)
        
        if current_policy:
            policies.append(current_policy)
        
        return policies
    
    def _parse_applied_policies(self, output):
        """Parse show policy-map interface output"""
        applied = []
        current_interface = None
        
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            
            if line.startswith('GigabitEthernet') or line.startswith('FastEthernet'):
                if current_interface:
                    applied.append(current_interface)
                
                current_interface = {
                    'interface': line,
                    'policies': []
                }
            
            elif 'Service-policy input:' in line and current_interface:
                policy_name = line.split('Service-policy input:')[-1].strip()
                current_interface['policies'].append({
                    'direction': 'input',
                    'name': policy_name
                })
            
            elif 'Service-policy output:' in line and current_interface:
                policy_name = line.split('Service-policy output:')[-1].strip()
                current_interface['policies'].append({
                    'direction': 'output',
                    'name': policy_name
                })
        
        if current_interface:
            applied.append(current_interface)
        
        return applied
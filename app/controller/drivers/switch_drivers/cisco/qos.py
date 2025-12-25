import re

class CiscoQoSDriver:
    def __init__(self, config):
        self.config = config
        self.base = None
    
    def set_base(self, base):
        """Set base SSH connection"""
        self.base = base
    
    def set_rate_limit(self, interface, rate_kbps, direction='input', logger=None):
        """Set rate limiting on interface"""
        try:
            policy = f"RL_{interface.replace('/', '_')}"
            if logger:
                logger(f"Setting rate limit on {interface} to {rate_kbps} kbps...")
            
            # Convert kbps to Mbps jika perlu
            rate_bps = rate_kbps * 1000

            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"policy-map {policy}", enable_mode=True)
            self.base.execute_command("class class-default", enable_mode=True)
            self.base.execute_command(f"police {rate_bps} conform-action transmit exceed-action drop", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            self.base.execute_command(f"interface {interface}", enable_mode=True)
            self.base.execute_command(f"service-policy {direction} {policy}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)

            save_result = self.base.save_configuration()
            
            if logger:
                logger(f"Rate limit {rate_kbps} kbps set on {interface}")
            
            return {
                'status': 'success',
                'message': f'Rate limit {rate_kbps} kbps set on {interface}',
                'interface': interface,
                'rate_kbps': rate_kbps,
                'rate_mbps': rate_bps,
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

        self.base.execute_command("configure terminal", enable_mode=True)
        self.base.execute_command(f"interface {interface}", enable_mode=True)
        self.base.execute_command(f"service-policy input limit-{interface}", enable_mode=True)
        self.base.execute_command("exit", enable_mode=True)
        self.base.execute_command("configure terminal", enable_mode=True)
        self.base.execute_command(f"policy-map limit-{interface}", enable_mode=True)
        self.base.execute_command(f"class class-default", enable_mode=True)
        self.base.execute_command(f"police {rate_bps} conform-action transmit exceed-action drop", enable_mode=True)
        self.base.execute_command("exit", enable_mode=True)
        self.base.execute_command("end", enable_mode=True)
        
        save_result = self.base.save_configuration()
        
        return {
            'status': 'success',
            'message': f'Rate limit {rate_kbps} kbps set using police method',
            'method': 'police'
        }

    def get_rate_limit(self, interface=None, logger=None):
        if logger:
            logger("Checking rate limit configuration (policy-map based)...")

        limits = []

        # 1. Ambil policy yang ter-apply ke interface
        out_intf = self.base.execute_command(
            "show policy-map interface", enable_mode=True
        )

        policy_map = None
        for line in out_intf.splitlines():
            line = line.strip()
            if interface and interface in line:
                continue
            if line.startswith("Service-policy input:"):
                policy_map = line.split(":")[-1].strip()
                break

        if not policy_map:
            return {"status": "success", "rate_limits": []}

        # 2. Ambil detail policy-map
        out_policy = self.base.execute_command(
            f"show policy-map {policy_map}", enable_mode=True
        )

        for line in out_policy.splitlines():
            line = line.strip()
            if line.startswith("police"):
                m = re.search(r'police\s+(\d+)', line)
                if m:
                    rate_bps = int(m.group(1))
                    limits.append({
                        "interface": interface,
                        "direction": "input",
                        "rate_kbps": rate_bps // 1000,
                        "policy": policy_map
                    })

        return {
            "status": "success",
            "rate_limits": limits
        }
    
    def create_qos_policy(self, policy_name, class_maps, logger=None):
        """Create QoS policy map"""
        try:
            if logger:
                logger(f"Creating QoS policy {policy_name}...")

            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"policy-map {policy_name}", enable_mode=True)
            
            for class_name, bandwidth_percent in class_maps.items():
                self.base.execute_command(f"class {class_name}", enable_mode=True)
                self.base.execute_command(f"bandwith percent {bandwidth_percent}", enable_mode=True)
                self.base.execute_command("exit", enable_mode=True)
            
            self.base.execute_command("end", enable_mode=True)
            
            save_result = self.base.save_configuration()
            
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

            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {interface}", enable_mode=True)
            self.base.execute_command(f"service-policy {direction} {policy_name}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            save_result = self.base.save_configuration()
            
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
            
            if line.startswith('GigabitEthernet') or line.startswith('FastEthernet') or line.startswith('Ethernet'):
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
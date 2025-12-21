from drivers.switch_drivers.cisco import CiscoSSHDriver  # Ganti dari CiscoNetconfDriver
from drivers.snmp_file_manager import SNMPFileManager
import json
import datetime

class CiscoSwitchActions:
    
    @staticmethod
    def get_actions(driver):
        # Pastikan semua modules terhubung ke base
        if driver.base:
            modules = [
                driver.interface, driver.vlan, driver.stp,
                driver.qos, driver.security, driver.lldp,
                driver.system, driver.snmp
            ]
            
            for module in modules:
                if hasattr(module, 'set_base'):
                    module.set_base(driver.base)
                elif hasattr(module, 'base'):
                    module.base = driver.base
        
        return {
            # === System & Discovery ===
            "switch.discovery": lambda p, logger: driver.get_device_info(),
            "switch.info": lambda p, logger: driver.get_device_info(),
            "switch.system.info": lambda p, logger: driver.system.get_system_info(logger),
            "switch.test.connection": lambda p, logger: driver.test_connection(),
            
            # === Interface Management ===
            "switch.interface.list": lambda p, logger: driver.interface.get_interfaces(logger),
            "switch.interface.configure": lambda p, logger: driver.interface.configure_interface(
                p['interface'], p, logger
            ),
            "switch.interface.enable": lambda p, logger: driver.interface.enable_interface(
                p['interface'], logger
            ),
            "switch.interface.disable": lambda p, logger: driver.interface.disable_interface(
                p['interface'], logger
            ),
            
            # === VLAN Management ===
            "switch.vlan.list": lambda p, logger: driver.vlan.get_vlans(logger),
            "switch.vlan.create": lambda p, logger: driver.vlan.create_vlan(
                p['vlan_id'], p.get('name'), logger
            ),
            "switch.vlan.delete": lambda p, logger: driver.vlan.delete_vlan(
                p['vlan_id'], logger
            ),
            "switch.vlan.assign.access": lambda p, logger: driver.vlan.assign_vlan_access(
                p['interface'], p['vlan_id'], logger
            ),
            "switch.vlan.assign.trunk": lambda p, logger: CiscoSwitchActions._assign_vlan_trunk(driver, p, logger),
            
            # === STP Management ===
            "switch.stp.info": lambda p, logger: driver.stp.get_stp_info(logger),
            "switch.stp.enable": lambda p, logger: driver.stp.enable_stp(logger),
            "switch.stp.disable": lambda p, logger: driver.stp.disable_stp(logger),
            "switch.stp.set.priority": lambda p, logger: driver.stp.set_bridge_priority(
                p['priority'], p.get('vlan'), logger
            ),
            "switch.stp.portfast": lambda p, logger: driver.stp.configure_portfast(
                p.get('interface'), logger
            ),
            
            # === LLDP Management ===
            "switch.lldp.neighbors": lambda p, logger: driver.lldp.get_lldp_neighbors(logger),
            "switch.lldp.enable": lambda p, logger: driver.lldp.enable_lldp(
                p.get('interface'), logger
            ),
            "switch.lldp.disable": lambda p, logger: driver.lldp.disable_lldp(
                p.get('interface'), logger
            ),
            "switch.lldp.status": lambda p, logger: driver.lldp.get_lldp_status(logger),
            
            # === QoS Management ===
            "switch.qos.rate.limit": lambda p, logger: driver.qos.set_rate_limit(
                p['interface'], p['rate_kbps'], p.get('direction', 'both'), logger
            ),
            "switch.qos.policy.create": lambda p, logger: driver.qos.create_qos_policy(
                p['policy_name'], p.get('class_maps', {}), logger
            ),
            "switch.qos.policy.apply": lambda p, logger: driver.qos.apply_qos_policy(
                p['interface'], p['policy_name'], p.get('direction', 'input'), logger
            ),
            "switch.qos.policies.list": lambda p, logger: driver.qos.get_qos_status(logger),
            
            # === Security ===
            "switch.security.enable": lambda p, logger: driver.security.enable_port_security(
                p['interface'], p.get('max_mac', 1), p.get('violation', 'shutdown'), logger
            ),
            "switch.security.disable": lambda p, logger: driver.security.disable_port_security(
                p['interface'], logger
            ),
            "switch.security.sticky.mac": lambda p, logger: driver.security.enable_sticky_mac(
                p['interface'], logger
            ),
            "switch.security.static.mac": lambda p, logger: driver.security.add_static_mac(
                p['interface'], p['mac_address'], p.get('vlan', 1), logger
            ),
            "switch.security.status": lambda p, logger: driver.security.get_port_security_status(
                p.get('interface'), logger
            ),
            "switch.security.clear": lambda p, logger: driver.security.clear_port_security(
                p['interface'], logger
            ),
            
            # === SNMP Management ===
            "switch.snmp.config.get": lambda p, logger: driver.snmp.get_snmp_info(p, logger),
            "switch.snmp.config.edit": lambda p, logger: driver.snmp.configure_snmp(p, logger),
            "switch.snmp.community.list": lambda p, logger: driver.snmp.list_communities(p, logger),
            "switch.snmp.community.add": lambda p, logger: driver.snmp.add_community(p, logger),
            "switch.snmp.community.edit": lambda p, logger: driver.snmp.edit_community(p, logger),
            "switch.snmp.community.delete": lambda p, logger: driver.snmp.delete_community(p, logger),
            "switch.snmp.enable": lambda p, logger: driver.snmp.enable_snmp(p, logger),
            "switch.snmp.disable": lambda p, logger: driver.snmp.disable_snmp(p, logger),
            
            # === Configuration ===
            "switch.config.backup": lambda p, logger: CiscoSwitchActions._backup_config(driver, p, logger),
            "switch.config.save": lambda p, logger: driver.system.save_config(logger),
            "switch.config.running": lambda p, logger: driver.system.get_running_config(logger),
            "switch.reboot": lambda p, logger: driver.system.reboot(logger),
            
            # === Monitoring ===
            "switch.monitoring.enable": lambda p, logger: CiscoSwitchActions._enable_monitoring(driver, p, logger),
        }
    
    # === Helper Methods ===
    
    @staticmethod
    def _assign_vlan_trunk(driver, params, logger):
        """Assign VLAN trunk configuration via SSH"""
        interface = params['interface']
        native_vlan = params.get('native_vlan', 1)
        allowed_vlans = params.get('allowed_vlans', 'all')
        
        config_commands = [
            f"interface {interface}",
            "switchport mode trunk",
            f"switchport trunk native vlan {native_vlan}",
            f"switchport trunk allowed vlan {allowed_vlans}",
            "exit"
        ]
        
        try:
            result = driver.base.execute_command(config_commands)
            
            if logger:
                logger(f"Configured trunk on {interface}: native {native_vlan}, allowed {allowed_vlans}")
            
            return {
                'status': 'success',
                'message': f'Trunk configured on {interface}',
                'interface': interface,
                'native_vlan': native_vlan,
                'allowed_vlans': allowed_vlans,
                'commands': config_commands
            }
            
        except Exception as e:
            if logger:
                logger(f"Error configuring trunk: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def _configure_snmp(driver, params, logger):
        """Configure SNMP with auto-add to Prometheus"""
        try:
            # First configure on switch
            result = driver.snmp.configure_snmp(params, logger)
            
            # Then add to Prometheus SNMP targets
            if result.get('status') == 'success' and 'community' in params:
                try:
                    device_info = driver.get_device_info()
                    
                    snmp_mgr = SNMPFileManager()
                    snmp_mgr.add_device({
                        "device_id": driver.config.get('device_id', 'unknown'),
                        "ip": driver.config['ip'],
                        "module": "cisco",
                        "device_name": device_info.get('hostname', 'Cisco-Switch'),
                        "community": params['community'],
                        "location": params.get('location', 'Unknown')
                    })
                    
                    if logger:
                        logger(f"Added switch to Prometheus SNMP targets")
                    
                except Exception as snmp_err:
                    if logger:
                        logger(f"Warning: Could not add to SNMP targets: {snmp_err}")
            
            return result
            
        except Exception as e:
            if logger:
                logger(f"Error configuring SNMP: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def _backup_config(driver, params, logger):
        """Backup switch configuration via SSH"""
        try:
            # Get running config via SSH
            config = driver.base.execute_command("show running-config", enable_mode=True)
            
            # Save to file or return as string
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if logger:
                logger(f"Configuration backed up at {timestamp}")
            
            return {
                'status': 'success',
                'message': 'Configuration backed up',
                'timestamp': timestamp,
                'config_size': len(config),
                'config_preview': config[:500]  # Preview 500 characters
            }
            
        except Exception as e:
            if logger:
                logger(f"Error backing up config: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def _restore_config(driver, params, logger):
        """Restore configuration (placeholder)"""
        try:
            if logger:
                logger("Restore configuration feature not yet implemented for SSH")
            
            return {
                'status': 'warning',
                'message': 'Restore feature not yet implemented for SSH driver',
                'note': 'Use console connection for configuration restore'
            }
            
        except Exception as e:
            if logger:
                logger(f"Error in restore config: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def _enable_monitoring(driver, params, logger):
        """Enable monitoring features"""
        actions = []
        
        try:
            # Enable SNMP
            if params.get('enable_snmp', True):
                snmp_params = {
                    'community': params.get('snmp_community', 'public'),
                    'location': params.get('location', 'Unknown'),
                    'contact': params.get('contact', 'Admin')
                }
                result = driver.snmp.configure_snmp(snmp_params, logger)
                if result.get('status') == 'success':
                    actions.append('SNMP enabled')
            
            # Enable LLDP
            if params.get('enable_lldp', True):
                result = driver.lldp.enable_lldp(logger=logger)
                if result.get('status') == 'success':
                    actions.append('LLDP enabled')
            
            # Enable STP
            if params.get('enable_stp', True):
                result = driver.stp.enable_stp(logger=logger)
                if result.get('status') == 'success':
                    actions.append('STP enabled')
            
            if logger:
                logger(f"Enabled monitoring features: {', '.join(actions)}")
            
            return {
                'status': 'success',
                'message': 'Monitoring features enabled',
                'actions': actions
            }
            
        except Exception as e:
            if logger:
                logger(f"Error enabling monitoring: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
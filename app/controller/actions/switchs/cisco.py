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
                driver.system, driver.snmp, driver.users, 
                driver.logging
            ]
            
            for module in modules:
                if hasattr(module, 'set_base'):
                    module.set_base(driver.base)
                elif hasattr(module, 'base'):
                    module.base = driver.base
        
        return {
            # === System & Discovery ===
            "switch.cisco.discovery": lambda p, logger: driver.get_device_info(),
            "switch.cisco.info": lambda p, logger: driver.get_device_info(),
            "switch.cisco.system.info": lambda p, logger: driver.system.get_system_info(logger),
            "switch.cisco.test.connection": lambda p, logger: driver.test_connection(),
            
            # === Interface Management ===
            "switch.cisco.interface.list": lambda p, logger: driver.interface.get_interfaces(logger),
            "switch.cisco.interface.configure": lambda p, logger: driver.interface.configure_interface(
                p['interface'], p, logger
            ),
            "switch.cisco.interface.enable": lambda p, logger: driver.interface.enable_interface(
                p['interface'], logger
            ),
            "switch.cisco.interface.disable": lambda p, logger: driver.interface.disable_interface(
                p['interface'], logger
            ),
            
            # === VLAN Management ===
            "switch.cisco.vlan.list": lambda p, logger: driver.vlan.get_vlans(logger),
            "switch.cisco.vlan.create": lambda p, logger: driver.vlan.create_vlan(
                p['vlan_id'], p.get('name'), logger
            ),
            "switch.cisco.vlan.delete": lambda p, logger: driver.vlan.delete_vlan(
                p['vlan_id'], logger
            ),
            "switch.cisco.vlan.assign.access": lambda p, logger: driver.vlan.assign_vlan_access(
                p['interface'], p['vlan_id'], logger
            ),
            "switch.cisco.vlan.assign.trunk": lambda p, logger: CiscoSwitchActions._assign_vlan_trunk(driver, p, logger),
            
            # === STP Management ===
            "switch.cisco.stp.info": lambda p, logger: driver.stp.get_stp_info(logger),
            "switch.cisco.stp.enable": lambda p, logger: driver.stp.enable_stp(logger),
            "switch.cisco.stp.vlan.enable": lambda p, logger: driver.stp.enable_stp_vlan(
                p['vlan'], logger
            ),
            "switch.cisco.stp.vlan.disable": lambda p, logger: driver.stp.disable_stp_vlan(
                p['vlan'], logger
            ),
            "switch.cisco.stp.vlan.priority": lambda p, logger: driver.stp.set_bridge_priority(
                p['priority'], p['vlan'], logger
            ),
            "switch.cisco.stp.interface.portfast": lambda p, logger: driver.stp.configure_portfast(
                p.get('interface'), logger
            ),
            
            # === LLDP Management ===
            "switch.cisco.lldp.neighbors": lambda p, logger: driver.lldp.get_lldp_neighbors(logger),
            "switch.cisco.lldp.enable": lambda p, logger: driver.lldp.enable_lldp(
                p.get('interface'), logger
            ),
            "switch.cisco.lldp.disable": lambda p, logger: driver.lldp.disable_lldp(
                p.get('interface'), logger
            ),
            "switch.cisco.lldp.status": lambda p, logger: driver.lldp.get_lldp_status(logger),
            
            # === QoS Management ===
            "switch.cisco.qos.rate.limit": lambda p, logger: driver.qos.set_rate_limit(
                p['interface'], p['rate_kbps'], p.get('direction', 'both'), logger
            ),
            "switch.cisco.qos.get.rate.limit": lambda p, logger: driver.qos.get_rate_limit(
                p.get("interface"), logger
            ),
            "switch.cisco.qos.policy.create": lambda p, logger: driver.qos.create_qos_policy(
                p['policy_name'], p.get('class_maps', {}), logger
            ),
            "switch.cisco.qos.policy.apply": lambda p, logger: driver.qos.apply_qos_policy(
                p['interface'], p['policy_name'], p.get('direction', 'input'), logger
            ),
            "switch.cisco.qos.policies.list": lambda p, logger: driver.qos.get_qos_status(logger),
            
            # === Security ===
            "switch.cisco.security.enable": lambda p, logger: driver.security.enable_port_security(
                p['interface'], p.get('max_mac', 1), p.get('violation', 'restrict'), logger
            ),
            "switch.cisco.security.disable": lambda p, logger: driver.security.disable_port_security(
                p['interface'], logger
            ),
            "switch.cisco.security.sticky.mac": lambda p, logger: driver.security.enable_sticky_mac(
                p['interface'], logger
            ),
            "switch.cisco.security.static.mac": lambda p, logger: driver.security.add_static_mac(
                p['interface'], p['mac_address'], p.get('vlan', 1), logger
            ),
            "switch.cisco.security.status": lambda p, logger: driver.security.get_port_security_status(
                p.get('interface'), logger
            ),
            "switch.cisco.security.clear": lambda p, logger: driver.security.clear_port_security(
                p['interface'], logger
            ),
            
            # === SNMP Management ===
            "switch.cisco.snmp.config.get": lambda p, logger: driver.snmp.get_snmp_info(p, logger),
            "switch.cisco.snmp.config.edit": lambda p, logger: driver.snmp.configure_snmp(p, logger),
            "switch.cisco.snmp.community.list": lambda p, logger: driver.snmp.list_communities(p, logger),
            "switch.cisco.snmp.community.add": lambda p, logger: driver.snmp.add_community(p, logger),
            "switch.cisco.snmp.community.edit": lambda p, logger: driver.snmp.edit_community(p, logger),
            "switch.cisco.snmp.community.delete": lambda p, logger: driver.snmp.delete_community(p, logger),
            "switch.cisco.snmp.enable": lambda p, logger: driver.snmp.enable_snmp(p, logger),
            "switch.cisco.snmp.disable": lambda p, logger: driver.snmp.disable_snmp(p, logger),

            # === Users Management ===
            "switch.cisco.users.list": lambda p, logger: driver.users.get_user_list(logger),
            "switch.cisco.user.create": lambda p, logger: driver.users.create_user(
                p['username'], p['password'], p.get('privilege_level', 1), logger
            ),
            "switch.cisco.user.update.password": lambda p, logger: driver.users.update_user_password(
                p['username'], p['new_password'], logger
            ),
            "switch.cisco.user.update.privilege": lambda p, logger: driver.users.update_user_privilege(
                p['username'], p['privilege_level'], logger
            ),
            "switch.cisco.user.delete": lambda p, logger: driver.users.delete_user(
                p['username'], logger
            ),

            # === Logging Management
            "switch.cisco.logging.status": lambda p, logger: driver.logging.get_logging_status(logger),
            "switch.cisco.logging.syslog.configure": lambda p, logger: driver.logging.configure_syslog(
                syslog_server=p['syslog_server'],
                facility=p.get('facility', 'local7'),
                severity=p.get('severity', 'informational'),
                port=p.get('port', 514),
                protocol=p.get('protocol', 'udp'),
                logger=logger
            ),
            "switch.cisco.logging.syslog.enable": lambda p, logger: (driver.logging.enable_syslog(logger)),
            "switch.cisco.logging.syslog.disable": lambda p, logger: driver.logging.disable_syslog(logger),
            "switch.cisco.logging.severity.set": lambda p, logger: driver.logging.set_logging_severity(
                p['severity'], logger
            ),
            
            # === System Configuration ===
            "switch.cisco.system.config.get": lambda p, logger: driver.system.get_running_config(logger),
            "switch.cisco.system.reboot": lambda p, logger: driver.system.reboot(logger=logger,
                confirm=p.get("confirm", False),
                user=p.get("user", "unknown")
            ),
        }
    
    # === Helper Methods ===
    
    @staticmethod
    def _assign_vlan_trunk(driver, params, logger):
        try:
            interface = params['interface']
            native_vlan = params.get('native_vlan', 1)
            allowed_vlans = params.get('allowed_vlans', 'all')

            if isinstance(allowed_vlans, list):
                allowed_vlans = ",".join(map(str, allowed_vlans))

            if logger:
                logger(f"Configuring trunk on {interface}")

            driver.base.execute_command("configure terminal", enable_mode=True)
            driver.base.execute_command(f"interface {interface}", enable_mode=True)
            driver.base.execute_command("switchport mode trunk", enable_mode=True)
            driver.base.execute_command(f"switchport trunk native vlan {native_vlan}", enable_mode=True)
            driver.base.execute_command(f"switchport trunk allowed vlan {allowed_vlans}", enable_mode=True)
            driver.base.execute_command("exit", enable_mode=True)
            driver.base.execute_command("end", enable_mode=True)

            # Verifikasi Commandnya
            verify = driver.base.execute_command(
                "show interface trunk",
                enable_mode=True
            )

            if interface not in verify:
                raise Exception("Trunk configuration verification failed")

            driver.base.execute_command("write memory", enable_mode=True)

            if logger:
                logger(f"Trunk successfully configured on {interface}")

            return {
                "status": "success",
                "interface": interface,
                "mode": "trunk",
                "native_vlan": native_vlan,
                "allowed_vlans": allowed_vlans
            }

        except Exception as e:
            if logger:
                logger(f"Error configuring trunk on {interface}: {e}")

            return {
                "status": "error",
                "error": str(e)
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
                        "device_name": device_info.get('identity', 'Cisco-Switch'),
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
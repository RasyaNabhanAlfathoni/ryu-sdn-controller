from drivers.switch_drivers.cisco import CiscoSSHDriver  # Ganti dari CiscoNetconfDriver
from drivers.snmp_file_manager import SNMPFileManager
from database.device_repository import DeviceRepository
import json
import datetime

class CiscoSwitchActions:

    @staticmethod
    def detect_switch_type(driver, logger=None):
        """Simple but reliable L2/L3 detection"""
        try:
            if logger:
                logger("Detecting switch type (L2/L3)...")
            
            # Gunakan method baru di driver jika ada
            if hasattr(driver, 'get_device_type'):
                device_type = driver.get_device_type()
                if logger:
                    logger(f"Device type from driver: {device_type}")
                return device_type
            
            return 'L2'
        except Exception as e:
            if logger:
                logger(f"Detection error, default to L2: {e}")
            return 'L2'
    
    @staticmethod
    def get_actions(driver, device_type=None):
        # Auto-detect jika tidak ditentukan
        if device_type is None:
            device_type = CiscoSwitchActions.detect_switch_type(driver)

        # Pastikan semua modules terhubung ke base
        if driver.base:
            modules = [
                driver.interface, driver.vlan, driver.stp,
                driver.qos, driver.security, driver.lldp,
                driver.system, driver.snmp, driver.users, 
                driver.logging
            ]

            if device_type == 'L3':
                if hasattr(driver, 'l3') and driver.l3 is not None:
                    modules.append(driver.l3)
                    # Set base untuk L3 module
                    if hasattr(driver.l3, 'set_base'):
                        driver.l3.set_base(driver.base)
                    elif hasattr(driver.l3, 'base'):
                        driver.l3.base = driver.base
            else:
                # Jika L3 module tidak ada, ubah device_type ke L2
                device_type = 'L2'
                if hasattr(driver, 'logger'):
                    driver.logger("L3 module not available, falling back to L2")
            
            for module in modules:
                if hasattr(module, 'set_base'):
                    module.set_base(driver.base)
                elif hasattr(module, 'base'):
                    module.base = driver.base
        
        actions = {
            # === System & Discovery ===
            "switch.cisco.info": lambda p, logger: driver.get_device_info(),
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
            "switch.cisco.vlan.assign.trunk": lambda p, logger: driver.vlan.assign_vlan_trunk(
                p['interface'], p['native_vlan'], p['allowed_vlans'], logger
            ),
            
            # === STP Management ===
            "switch.cisco.stp.info": lambda p, logger: driver.stp.get_stp_info(logger),
            "switch.cisco.stp.enable": lambda p, logger: driver.stp.enable_stp(logger),
            "switch.cisco.stp.disable": lambda p, logger: driver.stp.disable_stp(logger),
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
            "switch.cisco.stp.interface.portfast.disable": lambda p, logger: driver.stp.disable_portfast(
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
                p['interface'], p['mac_address'], logger
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
                port=p.get('port', 15111),
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
            "switch.cisco.system.identity.set": lambda p, logger: CiscoSwitchActions._identity_auto_update(
                driver, "set_hostname", p, logger,
                lambda: driver.system.set_identity(p['hostname'], logger),
                "hostname"
            ),
            "switch.cisco.system.reboot": lambda p, logger: driver.system.reboot(logger=logger,
                confirm=p.get("confirm", False),
                user=p.get("user", "unknown")
            ),
        }

        # Tambahkan actions L3 jika device type L3
        if device_type == 'L3':
            if hasattr(driver, 'l3') and driver.l3 is not None:
                if not hasattr(driver.l3, 'base') or driver.l3.base is None:
                    driver.l3.set_base(driver.base)
                l3_actions = {
                    # === L3 IP Routing ===
                    "switch.cisco.l3.routing.enable": lambda p, logger: driver.l3.enable_ip_routing(logger),
                    "switch.cisco.l3.routing.disable": lambda p, logger: driver.l3.disable_ip_routing(logger),
                    "switch.cisco.l3.routing.status": lambda p, logger: driver.l3.get_routing_status(logger),
                    "switch.cisco.l3.routing.check": lambda p, logger: {
                        'status': 'success',
                        'device_type': 'L3',
                        'ip_routing_enabled': driver.l3.is_ip_routing_enabled(logger)
                    },
                    
                    # === SVI Management ===
                    "switch.cisco.l3.svi.create": lambda p, logger: driver.l3.create_svi(
                        p['vlan_id'], p['ip_address'], p['subnet_mask'], logger
                    ),
                    "switch.cisco.l3.svi.delete": lambda p, logger: driver.l3.delete_svi(
                        p['vlan_id'], logger
                    ),
                    "switch.cisco.l3.svi.list": lambda p, logger: driver.l3.get_svi_interfaces(logger),
                    "switch.cisco.l3.svi.configure": lambda p, logger: driver.l3.configure_svi(
                        p['vlan_id'], p.get('ip_address'), p.get('subnet_mask'), p.get('description'), logger
                    ),
                    
                    # === Static Routing ===
                    "switch.cisco.l3.route.static.add": lambda p, logger: driver.l3.add_static_route(
                        p['network'], p['mask'], p['next_hop'], p['description'], logger
                    ),
                    "switch.cisco.l3.route.static.remove": lambda p, logger: driver.l3.remove_static_route(
                        p['network'], p['mask'], p['next_hop'], logger
                    ),
                    "switch.cisco.l3.route.static.list": lambda p, logger: driver.l3.get_static_routes(logger),
                    
                    # === Interface L3 Configuration ===
                    "switch.cisco.l3.interface.ip.configure": lambda p, logger: driver.l3.configure_interface_ip(
                        p['interface'], p['ip_address'], p['subnet_mask'], logger
                    ),
                    "switch.cisco.l3.interface.routed": lambda p, logger: driver.l3.convert_to_routed_port(
                        p['interface'], logger
                    ),
                    "switch.cisco.l3.interface.switched": lambda p, logger: driver.l3.convert_to_switched_port(
                        p['interface'], logger
                    ),
                    
                    # === ACL Management ===
                    "switch.cisco.l3.acl.standard.create": lambda p, logger: driver.l3.create_standard_acl(
                        p['acl_number'], logger
                    ),
                    "switch.cisco.l3.acl.standard.add_rule": lambda p, logger: driver.l3.add_standard_acl_rule(
                        p['acl_number'], p['action'], p['source'], logger
                    ),
                    "switch.cisco.l3.acl.extended.create": lambda p, logger: driver.l3.create_extended_acl(
                        p['acl_number'], logger
                    ),
                    "switch.cisco.l3.acl.extended.add_rule": lambda p, logger: driver.l3.add_extended_acl_rule(
                        p['acl_number'], p['action'], p['protocol'], p['source'], 
                        p['destination'], p.get('options'), logger
                    ),
                    "switch.cisco.l3.acl.apply": lambda p, logger: driver.l3.apply_acl_to_interface(
                        p['interface'], p['acl_number'], p['direction'], logger
                    ),
                    "switch.cisco.l3.acl.list": lambda p, logger: driver.l3.get_acls(logger),
                    
                    # === NTP ===
                    "switch.cisco.l3.ntp.configure": lambda p, logger: driver.l3.configure_ntp_server(
                        p['ntp_server'], logger
                    ),
                    "switch.cisco.l3.ntp.status": lambda p, logger: driver.l3.get_ntp_status(logger),
                }
                actions.update(l3_actions)
        
        return actions
    
    # === Helper Methods ===
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
        
    @staticmethod
    def _identity_auto_update(driver, action_name, params, logger, action_func, update_type):
        """Auto-update khusus untuk identity/hostname"""
        # Execute action dulu
        result = action_func()
        
        # Coba update database
        try:
            device_id = params.get("device_id") or getattr(driver, 'device_id', None)
            
            if not device_id and hasattr(driver, 'device_id'):
                device_id = driver.device_id
            
            if not device_id and hasattr(driver, 'config') and driver.config:
                device_id = driver.config.get('device_id')

            if not device_id:
                if logger:
                    logger(f"[AUTO-UPDATE] No device_id, skipping update")
                return result
            
            if action_name == "set_hostname" or action_name == "set_identity":
                hostname = params.get("identity", params.get("hostname", ""))
                
                if hostname:
                    if logger:
                        logger(f"[AUTO-UPDATE] Hostname changed to: {hostname}")
                    
                    # Update ke database
                    update_data = {
                        "identity": hostname,
                        "status": "active",
                        "last_seen": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    DeviceRepository.update_switch_partial(device_id, update_data)
                    if logger:
                        logger(f"[AUTO-UPDATE] Hostname updated in DB: {hostname}")
        
        except Exception as e:
            if logger:
                logger(f"[AUTO-UPDATE-WARNING] {e}")
        
        return result
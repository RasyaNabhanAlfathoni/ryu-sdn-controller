from drivers.server_drivers.server_api import ServerAPI
from drivers.wazuh_drivers.wazuh_api import WazuhAPI
from database.device_repository import DeviceRepository
import datetime

class ServerActions:

    @staticmethod
    def get_actions(d, wazuh_api=None):
        return {
            # ================= NETWORK MANAGEMENT =================
            # Interface actions
            "server.network.ip.add": lambda p, logger: d.add_ip(p.get("iface"), p.get("ip_cidr"), logger=logger),
            "server.network.ip.remove": lambda p, logger: d.del_ip(p.get("iface"), p.get("ip_cidr"), logger=logger),
            "server.network.interface.configure": lambda p, logger: ServerActions._configure_interface_with_guard(
                d, p, logger,
                lambda: d.configure_interface(
                    iface=p.get("iface"), 
                    ip_cidr=p.get("ip_cidr"),
                    gateway=p.get("gateway"),
                    dns_servers=p.get("dns_servers"),
                    onboot=p.get("onboot", True),
                    dhcp=p.get("dhcp", False),
                    logger=logger
                ),
            ),

            "server.network.interface.enable": lambda p, logger: d.enable_interface(p.get("iface"), logger=logger),
            "server.network.interface.disable": lambda p, logger: d.disable_interface(p.get("iface"), logger=logger),
            
            # Network info actions
            "server.network.interface.list": lambda p, logger: d.list_interfaces(logger=logger),
            "server.network.interface.info": lambda p, logger: d.get_ip_info(p.get("iface"), logger=logger),
            "server.network.port_scan": lambda p, logger: d.port_scan(p.get("target"), p.get("ports"), logger=logger),
            "server.network.routing_table": lambda p, logger: d.get_routing_table(logger=logger),
            "server.network.routing_add": lambda p, logger: d.add_route(
                network=p.get("network"),
                gateway=p.get("gateway"),
                interface=p.get("interface"),
                logger=logger
            ),
            "server.network.routing_delete": lambda p, logger: d.delete_route(
                network=p.get("network"),
                gateway=p.get("gateway"),
                interface=p.get("interface"),
                logger=logger
            ),
            # ================= FIREWALL MANAGEMENT =================
            # UFW actions
            "server.firewall.ufw.enable": lambda p, logger: d.ufw_enable(logger=logger),
            "server.firewall.ufw.disable": lambda p, logger: d.ufw_disable(logger=logger),
            "server.firewall.ufw.reload": lambda p, logger: d.ufw_reload(logger=logger),
            "server.firewall.ufw.reset": lambda p, logger: d.ufw_reset(logger=logger),
            "server.firewall.ufw.allow": lambda p, logger: d.ufw_allow(p.get("port_proto"), logger=logger),
            "server.firewall.ufw.deny": lambda p, logger: d.ufw_deny(p.get("port_proto"), logger=logger),
            "server.firewall.ufw.delete": lambda p, logger: d.ufw_delete(p.get("rule"), logger=logger),
            
            # Firewalld actions
            "server.firewall.firewalld.enable": lambda p, logger: d.firewalld_enable(logger=logger),
            "server.firewall.firewalld.disable": lambda p, logger: d.firewalld_disable(logger=logger),
            "server.firewall.firewalld.reload": lambda p, logger: d.firewall_reload(logger=logger),
            "server.firewall.firewalld.add_port": lambda p, logger: d.firewall_add_port(
                p.get("port_proto"), 
                p.get("zone", "public"),
                logger=logger
            ),
            "server.firewall.firewalld.remove_port": lambda p, logger: d.firewall_remove_port(
                p.get("port_proto"),
                p.get("zone", "public"),
                logger=logger
            ),
            "server.firewall.firewalld.enable_masquerade": lambda p, logger: d.firewall_enable_masquerade(
                p.get("zone", "public"),
                logger=logger
            ),
            "server.firewall.firewalld.disable_masquerade": lambda p, logger: d.firewall_disable_masquerade(
                p.get("zone", "public"),
                logger=logger
            ),
            "server.firewall.firewalld.command": lambda p, logger: d.firewall_cmd(
                p.get("args"),
                p.get("zone"),
                logger=logger
            ),
            
            # NAT actions
            "server.firewall.nat.list": lambda p, logger: d.get_nat_rules(logger=logger),
            "server.firewall.nat.add": lambda p, logger: d.setup_nat(p.get("interface"), logger=logger),
            "server.firewall.nat.clear": lambda p, logger: d.clear_nat(logger=logger),
            
            # Firewall info actions (tanpa auto-update)
            "server.firewall.ufw.status": lambda p, logger: d.ufw_status(logger=logger),
            "server.firewall.firewalld.status": lambda p, logger: d.firewall_status(logger=logger),
            "server.firewall.firewalld.list_ports": lambda p, logger: d.firewall_cmd("--list-ports", logger=logger),
            "server.firewall.firewalld.list_services": lambda p, logger: d.firewall_cmd("--list-services", logger=logger),
            "server.firewall.status": lambda p, logger: d.status_all(logger=logger),
            "server.firewall.detect_type": lambda p, logger: d.detect_firewall(logger=logger),
            "server.system.hostname.get": lambda p, logger: d.get_hostname(logger=logger),
            "server.system.hostname.set": lambda p, logger: ServerActions._simple_auto_update(
                d, "set_hostname", p, logger,
                lambda: d.set_hostname(
                    hostname=p.get("hostname"),
                    logger=logger
                ),
                "hostname"
            ),
            "server.system.reboot": lambda p, logger: d.reboot(
                delay_seconds=p.get("delay_seconds", 0),
                logger=logger
            ),
            
            # ================= SYSTEM MANAGEMENT =================
            # System info actions (tanpa auto-update)
            "server.system.logs": lambda p, logger: d.get_logs(p.get("lines", 50), logger=logger),
            "server.system.services.list": lambda p, logger: d.list_services(logger=logger),
            "server.system.services.control": lambda p, logger: d.service_control(p.get("service"), p.get("action"), logger=logger),
            "server.system.services.status": lambda p, logger: d.service_status(p.get("service"), logger=logger),

            # ================= USERS MANAGEMENT =================
            "server.system.users.list": lambda p, logger: d.get_users(logger=logger),
            "server.system.users.get": lambda p, logger: d.get_user_info(p.get("username"), logger=logger),
            "server.system.users.create": lambda p, logger: d.create_user(
                username=p.get("username"),
                password=p.get("password"),
                shell=p.get("shell", "/bin/bash"),
                home_dir=p.get("home_dir"),
                logger=logger
            ),
            "server.system.users.delete": lambda p, logger: d.delete_user(
                username=p.get("username"),
                remove_home=p.get("remove_home", False),
                logger=logger
            ),
            "server.system.users.modify": lambda p, logger: d.modify_user(
                username=p.get("username"),
                shell=p.get("shell"),
                home_dir=p.get("home_dir"),
                logger=logger
            ),
            "server.system.users.change_password": lambda p, logger: d.change_user_password(
                username=p.get("username"),
                password=p.get("password"),
                logger=logger
            ),
            "server.system.users.add_to_group": lambda p, logger: d.add_user_to_group(
                username=p.get("username"),
                group=p.get("group"),
                logger=logger
            ),
            "server.system.users.remove_from_group": lambda p, logger: d.remove_user_from_group(
                username=p.get("username"),
                group=p.get("group"),
                logger=logger
            ),
            "server.system.groups.list": lambda p, logger: d.get_groups(logger=logger),
            "server.system.groups.create": lambda p, logger: d.create_group(
                group_name=p.get("group_name"),
                logger=logger
            ),
            "server.system.groups.delete": lambda p, logger: d.delete_group(
                group_name=p.get("group_name"),
                logger=logger
            ),
            
            # ================= LLDP DISCOVERY =================
            # LLDP actions (tanpa auto-update)
            "server.network.lldp.neighbors": lambda p, logger: d.get_lldp_neighbors(
                iface=p.get('iface'), 
                logger=logger
            ),
            "server.network.lldp.statistics": lambda p, logger: d.get_lldp_statistics(logger=logger),
            "server.network.lldp.status": lambda p, logger: d.get_lldp_status(logger=logger),
            
            # ================= WAZUH AGENT =================
            # Wazuh actions
            "server.wazuh.agent.install": lambda p, logger: wazuh_api.install_agent(
                device_id=getattr(d, 'device_id', None) or p.get("device_id"),
                manager_ip=p.get("manager_ip"), 
                logger=logger
            ),
            "server.wazuh.agent.uninstall": lambda p, logger: wazuh_api.uninstall_agent(
                device_id=getattr(d, 'device_id', None) or p.get("device_id"),
                logger=logger
            ),
            "server.wazuh.agent.status": lambda p, logger: d.wazuh_agent_status(logger=logger),
            "server.wazuh.agent.start": lambda p, logger: d.wazuh_agent_start(logger=logger),
            "server.wazuh.agent.stop": lambda p, logger: d.wazuh_agent_stop(logger=logger),
            "server.wazuh.agent.config.get": lambda p, logger=None: d.wazuh_get_config(
                logger=logger
            ),
            "server.wazuh.agent.config.update": lambda p, logger=None: d.wazuh_update_config( 
                config_content=p["config_content"],
                logger=logger
            )
        }
    
    @staticmethod
    def _simple_auto_update(driver, action_name, params, logger, action_func, update_type):
        """Simple auto-update ke database setelah action"""
        # Execute action dulu
        result = action_func()
        
        # Coba update database
        try:
            device_id = getattr(driver, 'device_id', None) or params.get("device_id")
            
            if not device_id:
                logger(f"[AUTO-UPDATE] No device_id, skipping update")
                return result
            
            if update_type == "hostname":
                # Extract hostname dari result
                hostname = ""
                
                if action_name == "set_hostname":
                    hostname = params.get("hostname", "")
                
                if hostname:
                    logger(f"[AUTO-UPDATE] Detected hostname: {hostname}")
                    
                    # Update hostname ke database
                    try:
                        # Dapatkan data server saat ini
                        current_data = DeviceRepository.find_by_device_id(device_id)
                        if current_data:
                            current_hostname = current_data.get('hostname', '')
                            
                            # Cek apakah hostname berubah
                            if hostname and hostname != current_hostname:
                                update_data = {
                                    "hostname": hostname,
                                    "status": "active",
                                    "last_seen": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                }
                                
                                DeviceRepository.update_server_partial(device_id, update_data)
                                logger(f"[AUTO-UPDATE] Hostname updated in DB: {current_hostname} -> {hostname}")
                            else:
                                logger(f"[AUTO-UPDATE] Hostname unchanged: {hostname}")
                    except Exception as e:
                        logger(f"[AUTO-UPDATE-WARNING] Failed to update hostname: {e}")
            
        except Exception as e:
            # Jangan throw error, cukup log
            logger(f"[AUTO-UPDATE-WARNING] {e}")
        
        return result

    @staticmethod
    def _configure_interface_with_guard(driver, params, logger, action_func):
        """Prevention in IP pada main_interface"""
        device_id = getattr(driver, 'device_id', None) or params.get("device_id")
        iface = params.get("iface")
        ip_cidr = params.get("ip_cidr")
        
        if not device_id or not iface or not ip_cidr:
            return action_func()
        
        try:
            current_data = DeviceRepository.find_by_device_id(device_id)
            if not current_data:
                return action_func()
            
            main_iface = current_data.get("main_interface")
            main_ip = current_data.get("main_ip_address")
            
            if main_ip:
                new_ip = ip_cidr.split("/")[0]
                
                if iface == main_iface and new_ip != main_ip:
                    logger(
                        f"[GUARD] BLOCKED: Attempt to change MAIN interface "
                        f"{iface} IP {main_ip} -> {new_ip}"
                    )
                    # Return error
                    return {
                        "success": False,
                        "error": "Changing IP of main interface is not allowed. Please re-register or reconnect the device manually.",
                        "blocked": True,
                        "details": {
                            "interface": iface,
                            "current_ip": main_ip,
                            "attempted_ip": new_ip
                        }
                    }
        except Exception as e:
            logger(f"[GUARD-WARNING] {e}")
            # Jika guard gagal, tetap block untuk safety
            return {
                "success": False,
                "error": f"Guard check failed: {str(e)}",
                "blocked": True
            }
        
        # Hanya eksekusi jika tidak diblokir
        return action_func()

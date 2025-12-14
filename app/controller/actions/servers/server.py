from drivers.server_drivers.server_api import ServerAPI
from drivers.wazuh_drivers.wazuh_api import WazuhAPI
from database.device_repository import DeviceRepository

class ServerActions:

    @staticmethod
    def get_actions(d, wazuh_api=None):
        return {
            # ================= NETWORK MANAGEMENT =================
            # Interface actions dengan auto-update
            "server.network.ip.add": lambda p, logger: ServerActions._simple_auto_update(
                d, "add_ip", p, logger,
                lambda: d.add_ip(p.get("iface"), p.get("ip_cidr"), logger=logger),
                "interface"
            ),
            "server.network.ip.remove": lambda p, logger: ServerActions._simple_auto_update(
                d, "del_ip", p, logger,
                lambda: d.del_ip(p.get("iface"), p.get("ip_cidr"), logger=logger),
                "interface"
            ),
            "server.network.interface.configure": lambda p, logger: ServerActions._simple_auto_update(
                d, "configure_interface", p, logger,
                lambda: d.configure_interface(
                    iface=p.get("iface"), 
                    ip_cidr=p.get("ip_cidr"),
                    gateway=p.get("gateway"),
                    dns_servers=p.get("dns_servers"),
                    onboot=p.get("onboot", True),
                    dhcp=p.get("dhcp", False),
                    logger=logger
                ),
                "interface"
            ),
            "server.network.interface.enable": lambda p, logger: ServerActions._simple_auto_update(
                d, "enable_interface", p, logger,
                lambda: d.enable_interface(p.get("iface"), logger=logger),
                "interface"
            ),
            "server.network.interface.disable": lambda p, logger: ServerActions._simple_auto_update(
                d, "disable_interface", p, logger,
                lambda: d.disable_interface(p.get("iface"), logger=logger),
                "interface"
            ),
            
            # Network info actions (tanpa auto-update)
            "server.network.interface.info": lambda p, logger: d.get_ip_info(p.get("iface"), logger=logger),
            "server.network.port_scan": lambda p, logger: d.port_scan(p.get("target"), p.get("ports"), logger=logger),
            "server.network.routing_table": lambda p, logger: d.get_routing_table(logger=logger),
            
            # ================= FIREWALL MANAGEMENT =================
            # UFW actions dengan auto-update
            "server.firewall.ufw.enable": lambda p, logger: ServerActions._simple_auto_update(
                d, "ufw_enable", p, logger,
                lambda: d.ufw_enable(logger=logger),
                "firewall"
            ),
            "server.firewall.ufw.disable": lambda p, logger: ServerActions._simple_auto_update(
                d, "ufw_disable", p, logger,
                lambda: d.ufw_disable(logger=logger),
                "firewall"
            ),
            "server.firewall.ufw.reload": lambda p, logger: ServerActions._simple_auto_update(
                d, "ufw_reload", p, logger,
                lambda: d.ufw_reload(logger=logger),
                "firewall"
            ),
            "server.firewall.ufw.reset": lambda p, logger: ServerActions._simple_auto_update(
                d, "ufw_reset", p, logger,
                lambda: d.ufw_reset(logger=logger),
                "firewall"
            ),
            "server.firewall.ufw.allow": lambda p, logger: ServerActions._simple_auto_update(
                d, "ufw_allow", p, logger,
                lambda: d.ufw_allow(p.get("port_proto"), logger=logger),
                "firewall"
            ),
            "server.firewall.ufw.deny": lambda p, logger: ServerActions._simple_auto_update(
                d, "ufw_deny", p, logger,
                lambda: d.ufw_deny(p.get("port_proto"), logger=logger),
                "firewall"
            ),
            "server.firewall.ufw.delete": lambda p, logger: ServerActions._simple_auto_update(
                d, "ufw_delete", p, logger,
                lambda: d.ufw_delete(p.get("rule"), logger=logger),
                "firewall"
            ),
            "server.firewall.ufw.allow_in": lambda p, logger: ServerActions._simple_auto_update(
                d, "ufw_allow_in", p, logger,
                lambda: d.ufw("allow", "in", p.get("port_proto"), logger=logger),
                "firewall"
            ),
            "server.firewall.ufw.allow_out": lambda p, logger: ServerActions._simple_auto_update(
                d, "ufw_allow_out", p, logger,
                lambda: d.ufw("allow", "out", p.get("port_proto"), logger=logger),
                "firewall"
            ),
            "server.firewall.ufw.deny_in": lambda p, logger: ServerActions._simple_auto_update(
                d, "ufw_deny_in", p, logger,
                lambda: d.ufw("deny", "in", p.get("port_proto"), logger=logger),
                "firewall"
            ),
            "server.firewall.ufw.deny_out": lambda p, logger: ServerActions._simple_auto_update(
                d, "ufw_deny_out", p, logger,
                lambda: d.ufw("deny", "out", p.get("port_proto"), logger=logger),
                "firewall"
            ),
            
            # Firewalld actions dengan auto-update
            "server.firewall.firewalld.reload": lambda p, logger: ServerActions._simple_auto_update(
                d, "firewall_reload", p, logger,
                lambda: d.firewall_reload(logger=logger),
                "firewall"
            ),
            "server.firewall.firewalld.add_port": lambda p, logger: ServerActions._simple_auto_update(
                d, "firewall_add_port", p, logger,
                lambda: d.firewall_add_port(p.get("port_proto"), logger=logger),
                "firewall"
            ),
            "server.firewall.firewalld.remove_port": lambda p, logger: ServerActions._simple_auto_update(
                d, "firewall_remove_port", p, logger,
                lambda: d.firewall_remove_port(p.get("port_proto"), logger=logger),
                "firewall"
            ),
            "server.firewall.firewalld.enable_masquerade": lambda p, logger: ServerActions._simple_auto_update(
                d, "firewall_enable_masquerade", p, logger,
                lambda: d.firewall_enable_masquerade(logger=logger),
                "firewall"
            ),
            "server.firewall.firewalld.disable_masquerade": lambda p, logger: ServerActions._simple_auto_update(
                d, "firewall_disable_masquerade", p, logger,
                lambda: d.firewall_disable_masquerade(logger=logger),
                "firewall"
            ),
            "server.firewall.firewalld.command": lambda p, logger: ServerActions._simple_auto_update(
                d, "firewall_cmd", p, logger,
                lambda: d.firewall_cmd(p.get("args"), logger=logger),
                "firewall"
            ),
            
            # NAT actions dengan auto-update
            "server.firewall.nat.add": lambda p, logger: ServerActions._simple_auto_update(
                d, "setup_nat", p, logger,
                lambda: d.setup_nat(p.get("interface"), logger=logger),
                "firewall"
            ),
            "server.firewall.nat.clear": lambda p, logger: ServerActions._simple_auto_update(
                d, "clear_nat", p, logger,
                lambda: d.clear_nat(logger=logger),
                "firewall"
            ),
            
            # Firewall info actions (tanpa auto-update)
            "server.firewall.ufw.status": lambda p, logger: d.ufw_status(logger=logger),
            "server.firewall.firewalld.status": lambda p, logger: d.firewall_status(logger=logger),
            "server.firewall.firewalld.list_ports": lambda p, logger: d.firewall_cmd("--list-ports", logger=logger),
            "server.firewall.firewalld.list_services": lambda p, logger: d.firewall_cmd("--list-services", logger=logger),
            "server.firewall.status": lambda p, logger: d.status_all(logger=logger),
            "server.firewall.detect_type": lambda p, logger: d.detect_firewall(logger=logger),
            
            # ================= SYSTEM MANAGEMENT =================
            # System info actions (tanpa auto-update)
            "server.system.logs": lambda p, logger: d.get_logs(p.get("lines", 50), logger=logger),
            "server.system.services.list": lambda p, logger: d.list_services(logger=logger),
            "server.system.services.control": lambda p, logger: d.service_control(p.get("service"), p.get("action"), logger=logger),
            "server.system.services.status": lambda p, logger: d.service_status(p.get("service"), logger=logger),
            
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
            "server.wazuh.install": lambda p, logger: wazuh_api.install_agent(
                device_id=getattr(d, 'device_id', None) or p.get("device_id"),
                manager_ip=p.get("manager_ip"), 
                logger=logger
            ),
            "server.wazuh.uninstall": lambda p, logger: wazuh_api.uninstall_agent(
                device_id=getattr(d, 'device_id', None) or p.get("device_id"),
                logger=logger
            ),
            "server.wazuh.status": lambda p, logger: d.wazuh_agent_status(logger=logger),
        }
    
    @staticmethod
    def _simple_auto_update(driver, action_name, params, logger, action_func, update_type):
        """Simple auto-update ke database setelah action"""
        # 1. Execute action dulu
        result = action_func()
        
        # 2. Try to update database (jangan ganggu jika gagal)
        try:
            device_id = getattr(driver, 'device_id', None) or params.get("device_id")
            
            if not device_id:
                logger(f"[AUTO-UPDATE] No device_id, skipping update")
                return result
            
            if update_type == "firewall":
                # Get current firewall status
                firewall_status = driver.status_all(logger=logger)
                if firewall_status:
                    # Simple update ke database
                    DeviceRepository.update_server_firewall_state(
                        device_id=device_id,
                        firewall_state=firewall_status
                    )
                    logger(f"[AUTO-UPDATE] Firewall state updated in DB")
                    
            elif update_type == "interface":
                # Get interface name dari params
                iface = params.get("iface")
                if iface:
                    # DEBUG: Tunggu sebentar agar interface configuration settle
                    import time
                    time.sleep(5)  # Tunggu 5 detik
                    
                    logger(f"[AUTO-UPDATE] Getting interface info for {iface} after action")
                    
                    # Get current interface info
                    interface_info = driver.get_ip_info(iface, logger=logger)
                    
                    # DEBUG: Cek data yang dikembalikan
                    logger(f"[AUTO-UPDATE] Interface info from agent: {interface_info}")
                    logger(f"[AUTO-UPDATE] Type: {type(interface_info)}")
                    
                    if interface_info:
                        # Perbaiki jika data tidak lengkap
                        if isinstance(interface_info, dict):
                            if "status" not in interface_info or interface_info["status"] == "unknown":
                                logger(f"[AUTO-UPDATE] Status not found in response, detecting...")
                                
                                # Coba deteksi status berdasarkan action yang baru dilakukan
                                if action_name == "enable_interface":
                                    interface_info["status"] = "up"
                                elif action_name == "disable_interface":
                                    interface_info["status"] = "down"
                                else:
                                    # Default: unknown
                                    interface_info["status"] = "unknown"
                                    
                            # Jika address kosong, tapi ada IP di params, gunakan itu
                            if not interface_info.get("address") and "ip_cidr" in params:
                                try:
                                    # Extract IP dari ip_cidr
                                    ip_cidr = params["ip_cidr"]
                                    ip_address = ip_cidr.split("/")[0]
                                    interface_info["address"] = ip_address
                                    logger(f"[AUTO-UPDATE] Using IP from params: {ip_address}")
                                    
                                    # Hitung netmask dari CIDR
                                    cidr_prefix = int(ip_cidr.split("/")[1]) if "/" in ip_cidr else 24
                                    # Convert prefix to netmask
                                    mask = (0xffffffff << (32 - cidr_prefix)) & 0xffffffff
                                    netmask = f"{(mask >> 24) & 0xff}.{(mask >> 16) & 0xff}.{(mask >> 8) & 0xff}.{mask & 0xff}"
                                    interface_info["netmask"] = netmask
                                    logger(f"[AUTO-UPDATE] Calculated netmask: {netmask}")
                                except Exception as e:
                                    logger(f"[AUTO-UPDATE] Error extracting IP from params: {e}")
                            
                            # Hitung broadcast jika tidak ada
                            if "address" in interface_info and "netmask" in interface_info:
                                try:
                                    import ipaddress
                                    ip_addr = interface_info["address"]
                                    netmask = interface_info["netmask"]
                                    
                                    # Convert netmask to prefix
                                    if "." in netmask:
                                        prefix = sum(bin(int(x)).count('1') for x in netmask.split('.'))
                                    else:
                                        prefix = int(netmask)
                                    
                                    cidr = f"{ip_addr}/{prefix}"
                                    network = ipaddress.IPv4Network(cidr, strict=False)
                                    interface_info["ip_broadcast"] = str(network.broadcast_address)
                                    logger(f"[AUTO-UPDATE] Calculated broadcast: {interface_info['ip_broadcast']}")
                                except Exception as e:
                                    logger(f"[AUTO-UPDATE] Cannot calculate broadcast: {e}")
                                    interface_info["ip_broadcast"] = ""
                            
                            # Simple update ke database
                            success = DeviceRepository.update_interface_state(
                                device_id=device_id,
                                interface_name=iface,
                                interface_data=interface_info
                            )
                            logger(f"[AUTO-UPDATE] Interface {iface} update {'success' if success else 'failed'} in DB")
                        else:
                            logger(f"[AUTO-UPDATE] Interface info is not a dict: {type(interface_info)}")
                    else:
                        logger(f"[AUTO-UPDATE] No interface info returned from agent")
            
        except Exception as e:
            # Jangan throw error, cukup log
            logger(f"[AUTO-UPDATE-WARNING] {e}")
        
        return result
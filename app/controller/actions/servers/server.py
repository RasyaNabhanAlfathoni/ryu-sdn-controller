from drivers.server_drivers.server_api import ServerAPI
from drivers.wazuh_drivers.wazuh_api import WazuhAPI

class ServerActions:

    @staticmethod
    def get_actions(d, wazuh_api=None):
        return {
            # Network Management
                "server.network.list_interfaces": lambda p, logger: d.list_interfaces(logger=logger),
                "server.network.get_interface_details": lambda p, logger: d.get_interface_details(logger=logger),
                "server.network.ip.show_all": lambda p, logger: d.show_all(logger=logger),
                "server.network.ip.add": lambda p, logger: d.add_ip(p.get("iface"), p.get("ip_cidr"), logger=logger),
                "server.network.ip.remove": lambda p, logger: d.del_ip(p.get("iface"), p.get("ip_cidr"), logger=logger),
                "server.network.configure_interface": lambda p, logger: d.configure_interface(
                    iface=p.get("iface"), 
                    ip_cidr=p.get("ip_cidr"),
                    gateway=p.get("gateway"),
                    dns_servers=p.get("dns_servers"),
                    onboot=p.get("onboot", True),
                    dhcp=p.get("dhcp", False),
                    logger=logger
                ),
                "server.network.enable_interface": lambda p, logger: d.enable_interface(p.get("iface"), logger=logger),
                "server.network.disable_interface": lambda p, logger: d.disable_interface(p.get("iface"), logger=logger),
                "server.network.get_single_interface": lambda p, logger: d.get_ip_info(p.get("iface"), logger=logger),
                "server.network.get_interface_ips": lambda p, logger: d.get_interface_ips(p.get("iface"), logger=logger),
                "server.network.get_interface_status": lambda p, logger: d.get_interface_status(p.get("iface"), logger=logger),
                "server.network.connections": lambda p, logger: d.get_network_connections(logger=logger),
                "server.network.interface_counters": lambda p, logger: d.get_interface_counters(p.get("iface"), logger=logger),

                # Advanced Network Management 
                "server.network.port_scan": lambda p, logger: d.port_scan(p.get("target"), p.get("ports"), logger=logger),
                "server.network.routing_table": lambda p, logger: d.get_routing_table(logger=logger),
                "server.network.arp_table": lambda p, logger: d.get_arp_table(logger=logger),

                # LLDP Discovery
                "server.network.lldp.neighbors": lambda p, logger: d.get_lldp_neighbors(
                    iface=p.get('iface'), 
                    logger=logger
                ),
                "server.network.lldp.statistics": lambda p, logger: d.get_lldp_statistics(logger=logger),
                "server.network.lldp.status": lambda p, logger: d.get_lldp_status(logger=logger),

                # Firewall Management - UFW
                "server.firewall.ufw_status": lambda p, logger: d.ufw_status(logger=logger),
                "server.firewall.ufw_enable": lambda p, logger: d.ufw_enable(logger=logger),
                "server.firewall.ufw_disable": lambda p, logger: d.ufw_disable(logger=logger),
                "server.firewall.ufw_reload": lambda p, logger: d.ufw_reload(logger=logger),
                "server.firewall.ufw_reset": lambda p, logger: d.ufw_reset(logger=logger),
                "server.firewall.ufw_allow": lambda p, logger: d.ufw_allow(p.get("port_proto"), logger=logger),
                "server.firewall.ufw_deny": lambda p, logger: d.ufw_deny(p.get("port_proto"), logger=logger),
                "server.firewall.ufw_delete": lambda p, logger: d.ufw_delete(p.get("rule"), logger=logger),
                "server.firewall.ufw_allow_in": lambda p, logger: d.ufw("allow", "in", p.get("port_proto"), logger=logger),
                "server.firewall.ufw_allow_out": lambda p, logger: d.ufw("allow", "out", p.get("port_proto"), logger=logger),
                "server.firewall.ufw_deny_in": lambda p, logger: d.ufw("deny", "in", p.get("port_proto"), logger=logger),
                "server.firewall.ufw_deny_out": lambda p, logger: d.ufw("deny", "out", p.get("port_proto"), logger=logger),
                
                # Firewall Management - Firewalld
                "server.firewall.firewalld_status": lambda p, logger: d.firewall_status(logger=logger),
                "server.firewall.firewalld_reload": lambda p, logger: d.firewall_reload(logger=logger),
                "server.firewall.firewalld_add_port": lambda p, logger: d.firewall_add_port(p.get("port_proto"), logger=logger),
                "server.firewall.firewalld_remove_port": lambda p, logger: d.firewall_remove_port(p.get("port_proto"), logger=logger),
                "server.firewall.firewalld_enable_masquerade": lambda p, logger: d.firewall_enable_masquerade(logger=logger),
                "server.firewall.firewalld_disable_masquerade": lambda p, logger: d.firewall_disable_masquerade(logger=logger),
                "server.firewall.firewalld_list_ports": lambda p, logger: d.firewall_cmd("--list-ports", logger=logger),
                "server.firewall.firewalld_list_services": lambda p, logger: d.firewall_cmd("--list-services", logger=logger),
                "server.firewall.firewalld_command": lambda p, logger: d.firewall_cmd(p.get("args"), logger=logger),
                
                # Firewall Management - NAT & General
                "server.firewall.nat.add": lambda p, logger: d.setup_nat(p.get("interface"), logger=logger),
                "server.firewall.nat.clear": lambda p, logger: d.clear_nat(logger=logger),
                "server.firewall.status_all": lambda p, logger: d.status_all(logger=logger),
                "server.firewall.detect_type": lambda p, logger: d.detect_firewall(logger=logger),

                # System Management - Monitor
                "server.system.monitor": lambda p, logger: d.get_utilization(logger=logger),
                "server.system.monitor_detailed": lambda p, logger: d.get_detailed_utilization(logger=logger),
                "server.system.info": lambda p, logger: d.get_system_info(logger=logger),
                "server.system.logs": lambda p, logger: d.get_logs(p.get("lines", 50), logger=logger),
                
                # System Services
                "server.system.services.list": lambda p, logger: d.list_services(logger=logger),
                "server.system.services.control": lambda p, logger: d.service_control(p.get("service"), p.get("action"), logger=logger),
                "server.system.services.status": lambda p, logger: d.service_status(p.get("service"), logger=logger),

                # === Wazuh Agent Command ===
                "wazuh.agent.list": lambda p, logger: wazuh_api.get_agents(),
                "server.wazuh.install": lambda p, logger: wazuh_api.install_agent(
                    device_id=p.get("device_id"),
                    manager_ip=p.get("manager_ip"), 
                    logger=logger
                ),
                "server.wazuh.uninstall": lambda p, logger: wazuh_api.uninstall_agent(
                    device_id=p.get("device_id"),
                    logger=logger
                ),
                "server.wazuh.status": lambda p, logger: wazuh_api.get_agent_status(
                    device_id=p.get("device_id"),
                    logger=logger
                ),
                "server.wazuh.security.overview": lambda p, logger: wazuh_api.get_security_overview(
                    device_id=p.get("device_id"),
                    logger=logger
                ),
                "server.wazuh.security.vulnerabilities": lambda p, logger: wazuh_api.get_vulnerabilities(
                    agent_id=p.get("agent_id"),
                    logger=logger
                ),
                "server.wazuh.security.fim": lambda p, logger: wazuh_api.get_fim_data(
                    agent_id=p.get("agent_id"),
                    logger=logger
                ),
                "server.wazuh.security.events": lambda p, logger: wazuh_api.get_agent_security_events(
                    agent_id=p.get("agent_id"),
                    limit=p.get("limit", 50),
                    logger=logger
                ),
        }
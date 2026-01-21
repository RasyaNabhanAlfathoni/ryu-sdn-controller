from drivers.router_drivers.mikrotik.ip import RouterOSIpDriver
from drivers.router_drivers.mikrotik.interface import RouterOSInterfaceDriver
from drivers.router_drivers.mikrotik.vlan import RouterOSVlanDriver
from drivers.router_drivers.mikrotik.dhcp_server import RouterOSDhcpServerDriver
from drivers.router_drivers.mikrotik.dhcp_client import RouterOSDhcpClientDriver
from drivers.router_drivers.mikrotik.ip_pool import RouterOSIpPoolDriver
from drivers.router_drivers.mikrotik.dns_server import RouterOSDnsDriver
from drivers.router_drivers.mikrotik.neighbor import RouterOSNeighborDriver
from drivers.router_drivers.mikrotik.snmp import RouterOSSNMPDriver
from drivers.router_drivers.mikrotik.route import RouterOSRouteDriver
from drivers.router_drivers.mikrotik.users_manager import RouterOSUserManagerDriver
from drivers.router_drivers.mikrotik.queues import RouterOSQueuesDriver
from drivers.router_drivers.mikrotik.firewall import RouterOSFirewallDriver
from drivers.router_drivers.mikrotik.netwatch import RouterOSNetwatchDriver
from drivers.router_drivers.mikrotik.logging import RouterOSLoggingDriver
from drivers.snmp_file_manager import SNMPFileManager

class MikrotikRouterActions:

    @staticmethod
    def get_actions(d):

        return {
            # IP Address Management
            "router.mikrotik.ip.address.add": lambda p, logger: RouterOSIpDriver(d).add_address(p, logger),
            "router.mikrotik.ip.address.delete": lambda p, logger: RouterOSIpDriver(d).delete_address(p, logger),
            "router.mikrotik.ip.address.edit": lambda p, logger: RouterOSIpDriver(d).edit_address(p, logger),
            "router.mikrotik.ip.address.disable": lambda p, logger: RouterOSIpDriver(d).disable_address(p, logger),
            "router.mikrotik.ip.address.enable": lambda p, logger: RouterOSIpDriver(d).enable_address(p, logger),
            "router.mikrotik.ip.address.comment": lambda p, logger: RouterOSIpDriver(d).comment_address(p, logger),
            "router.mikrotik.ip.address.list": lambda p, logger: RouterOSIpDriver(d).list_addresses(p, logger),

            # IP POOL Management
            "router.mikrotik.ip.pool.add": lambda p, logger: RouterOSIpPoolDriver(d).add_pool(p, logger),
            "router.mikrotik.ip.pool.edit": lambda p, logger: RouterOSIpPoolDriver(d).edit_pool(p, logger),
            "router.mikrotik.ip.pool.delete": lambda p, logger: RouterOSIpPoolDriver(d).delete_pool(p, logger),
            "router.mikrotik.ip.pool.comment": lambda p, logger: RouterOSIpPoolDriver(d).comment_pool(p, logger),
            "router.mikrotik.ip.pool.list": lambda p, logger: RouterOSIpPoolDriver(d).list_pool(p, logger),

            # Interface Management
            "router.mikrotik.interface.add": lambda p, logger: RouterOSInterfaceDriver(d).add_interface(p, logger),
            "router.mikrotik.interface.edit": lambda p, logger: RouterOSInterfaceDriver(d).edit_interface(p, logger),
            "router.mikrotik.interface.disable": lambda p, logger: RouterOSInterfaceDriver(d).disable_interface(p, logger),
            "router.mikrotik.interface.enable": lambda p, logger: RouterOSInterfaceDriver(d).enable_interface(p, logger),
            "router.mikrotik.interface.comment": lambda p, logger: RouterOSInterfaceDriver(d).comment_interface(p, logger),
            "router.mikrotik.interface.cable_test": lambda p, logger: RouterOSInterfaceDriver(d).cable_test(p, logger),

            # VLAN Management
            "router.mikrotik.vlan.add": lambda p, logger: RouterOSVlanDriver(d).add_vlan(p, logger),
            "router.mikrotik.vlan.edit": lambda p, logger: RouterOSVlanDriver(d).edit_vlan(p, logger),
            "router.mikrotik.vlan.delete": lambda p, logger: RouterOSVlanDriver(d).delete_vlan(p, logger),
            "router.mikrotik.vlan.enable": lambda p, logger: RouterOSVlanDriver(d).enable_vlan(p, logger),
            "router.mikrotik.vlan.disable": lambda p, logger: RouterOSVlanDriver(d).disable_vlan(p, logger),
            "router.mikrotik.vlan.comment": lambda p, logger: RouterOSVlanDriver(d).comment_vlan(p, logger),

            # DHCP SERVER
            "router.mikrotik.dhcp.server.add": lambda p, logger: RouterOSDhcpServerDriver(d).add_server(p, logger),
            "router.mikrotik.dhcp.server.edit": lambda p, logger: RouterOSDhcpServerDriver(d).edit_server(p, logger),
            "router.mikrotik.dhcp.server.enable": lambda p, logger: RouterOSDhcpServerDriver(d).enable_server(p, logger),
            "router.mikrotik.dhcp.server.disable": lambda p, logger: RouterOSDhcpServerDriver(d).disable_server(p, logger),
            "router.mikrotik.dhcp.server.delete": lambda p, logger: RouterOSDhcpServerDriver(d).delete_server(p, logger),
            "router.mikrotik.dhcp.server.list": lambda p, logger: RouterOSDhcpServerDriver(d).list_servers(p, logger),
            "router.mikrotik.dhcp.network.edit": lambda p, logger: RouterOSDhcpServerDriver(d).edit_network(p, logger),
            "router.mikrotik.dhcp.network.list": lambda p, logger: RouterOSDhcpServerDriver(d).list_networks(p, logger),
            "router.mikrotik.dhcp.lease.list": lambda p, logger: RouterOSDhcpServerDriver(d).list_leases(p, logger),

            # DHCP CLIENT
            "router.mikrotik.dhcp.client.add": lambda p, logger: RouterOSDhcpClientDriver(d).add_client(p, logger),
            "router.mikrotik.dhcp.client.edit": lambda p, logger: RouterOSDhcpClientDriver(d).edit_client(p, logger),
            "router.mikrotik.dhcp.client.enable": lambda p, logger: RouterOSDhcpClientDriver(d).enable_client(p, logger),
            "router.mikrotik.dhcp.client.disable": lambda p, logger: RouterOSDhcpClientDriver(d).disable_client(p, logger),
            "router.mikrotik.dhcp.client.delete": lambda p, logger: RouterOSDhcpClientDriver(d).delete_client(p, logger),
            "router.mikrotik.dhcp.client.comment": lambda p, logger: RouterOSDhcpClientDriver(d).comment_client(p, logger),
            "router.mikrotik.dhcp.client.list": lambda p, logger: RouterOSDhcpClientDriver(d).list_client(p, logger),

            # DNS Configuration
            "router.mikrotik.dns.edit": lambda p, logger: RouterOSDnsDriver(d).edit_dns(p, logger),
            "router.mikrotik.dns.flush": lambda p, logger: RouterOSDnsDriver(d).flush_cache(p, logger),
            "router.mikrotik.dns.static.add": lambda p, logger: RouterOSDnsDriver(d).add_static(p, logger),
            "router.mikrotik.dns.static.edit": lambda p, logger: RouterOSDnsDriver(d).edit_static(p, logger),
            "router.mikrotik.dns.static.enable": lambda p, logger: RouterOSDnsDriver(d).enable_static(p, logger),
            "router.mikrotik.dns.static.disable": lambda p, logger: RouterOSDnsDriver(d).disable_static(p, logger),
            "router.mikrotik.dns.static.comment": lambda p, logger: RouterOSDnsDriver(d).comment_static(p, logger),
            "router.mikrotik.dns.static.delete": lambda p, logger: RouterOSDnsDriver(d).delete_static(p, logger),
            "router.mikrotik.dns.static.list": lambda p, logger: RouterOSDnsDriver(d).list_static(p, logger),

            # Neighbor
            "router.mikrotik.neighbor.get": lambda p, logger: RouterOSNeighborDriver(d).get_neighbors(p, logger),
            "router.mikrotik.neighbor.discovery.get": lambda p, logger: RouterOSNeighborDriver(d).get_discovery_settings(p, logger),
            "router.mikrotik.neighbor.discovery.edit": lambda p, logger: RouterOSNeighborDriver(d).edit_discovery_settings(p, logger),

            # SNMP RouterOS native config
            "router.mikrotik.snmp.config.get": lambda p, logger: RouterOSSNMPDriver(d).get_snmp_config(p, logger),
            "router.mikrotik.snmp.config.edit": lambda p, logger: RouterOSSNMPDriver(d).edit_snmp_config(p, logger),
            "router.mikrotik.snmp.community.list": lambda p, logger: RouterOSSNMPDriver(d).list_communities(p, logger),
            "router.mikrotik.snmp.community.add": lambda p, logger: RouterOSSNMPDriver(d).add_community(p, logger),
            "router.mikrotik.snmp.community.edit": lambda p, logger: RouterOSSNMPDriver(d).edit_community(p, logger),
            "router.mikrotik.snmp.community.delete": lambda p, logger: RouterOSSNMPDriver(d).delete_community(p, logger),
            "router.mikrotik.snmp.community.enable": lambda p, logger: RouterOSSNMPDriver(d).enable_community(p, logger),
            "router.mikrotik.snmp.community.disable": lambda p, logger: RouterOSSNMPDriver(d).disable_community(p, logger),
            "router.mikrotik.snmp.device.add": lambda p, logger: SNMPFileManager().add_device(p),

            # Route Management
            "router.mikrotik.route.list": lambda p, logger: RouterOSRouteDriver(d).list_routes(p, logger),
            "router.mikrotik.route.add": lambda p, logger: RouterOSRouteDriver(d).add_route(p, logger),
            "router.mikrotik.route.edit": lambda p, logger: RouterOSRouteDriver(d).edit_route(p, logger),
            "router.mikrotik.route.delete": lambda p, logger: RouterOSRouteDriver(d).delete_route(p, logger),
            "router.mikrotik.route.disable": lambda p, logger: RouterOSRouteDriver(d).disable_route(p, logger),
            "router.mikrotik.route.enable": lambda p, logger: RouterOSRouteDriver(d).enable_route(p, logger),
            "router.mikrotik.route.comment": lambda p, logger: RouterOSRouteDriver(d).enable_route(p, logger),

            # Users Management
            "router.mikrotik.user.list":     lambda p, logger: RouterOSUserManagerDriver(d).user_list(p, logger),
            "router.mikrotik.user.add":      lambda p, logger: RouterOSUserManagerDriver(d).user_add(p, logger),
            "router.mikrotik.user.edit":     lambda p, logger: RouterOSUserManagerDriver(d).user_edit(p, logger),
            "router.mikrotik.user.delete":   lambda p, logger: RouterOSUserManagerDriver(d).user_delete(p, logger),
            "router.mikrotik.user.enable":   lambda p, logger: RouterOSUserManagerDriver(d).user_enable(p, logger),
            "router.mikrotik.user.disable":  lambda p, logger: RouterOSUserManagerDriver(d).user_disable(p, logger),
            "router.mikrotik.user.comment":  lambda p, logger: RouterOSUserManagerDriver(d).user_comment(p, logger),
            "router.mikrotik.group.list":    lambda p, logger: RouterOSUserManagerDriver(d).group_list(p, logger),
            "router.mikrotik.group.add":     lambda p, logger: RouterOSUserManagerDriver(d).group_add(p, logger),
            "router.mikrotik.group.edit":    lambda p, logger: RouterOSUserManagerDriver(d).group_edit(p, logger),
            "router.mikrotik.group.delete":  lambda p, logger: RouterOSUserManagerDriver(d).group_delete(p, logger),
            "router.mikrotik.group.comment": lambda p, logger: RouterOSUserManagerDriver(d).group_comment(p, logger),
            "router.mikrotik.active.list":   lambda p, logger: RouterOSUserManagerDriver(d).active_list(p, logger),
            "router.mikrotik.active.logout":   lambda p, logger: RouterOSUserManagerDriver(d).active_logout(p, logger),

            # Queues Management
            "router.mikrotik.queue.simple.list":    lambda p, logger: RouterOSQueuesDriver(d).queue_simple_list(p, logger),
            "router.mikrotik.queue.simple.add":     lambda p, logger: RouterOSQueuesDriver(d).queue_simple_add(p, logger),
            "router.mikrotik.queue.simple.edit":    lambda p, logger: RouterOSQueuesDriver(d).queue_simple_edit(p, logger),
            "router.mikrotik.queue.simple.delete":  lambda p, logger: RouterOSQueuesDriver(d).queue_simple_delete(p, logger),
            "router.mikrotik.queue.simple.enable":  lambda p, logger: RouterOSQueuesDriver(d).queue_simple_enable(p, logger),
            "router.mikrotik.queue.simple.disable": lambda p, logger: RouterOSQueuesDriver(d).queue_simple_disable(p, logger),
            "router.mikrotik.queue.interface.list": lambda p, logger: RouterOSQueuesDriver(d).queue_interface_list(p, logger),
            "router.mikrotik.queue.interface.edit": lambda p, logger: RouterOSQueuesDriver(d).queue_interface_edit(p, logger),
            "router.mikrotik.queue.tree.list":      lambda p, logger: RouterOSQueuesDriver(d).queue_tree_list(p, logger),
            "router.mikrotik.queue.tree.add":       lambda p, logger: RouterOSQueuesDriver(d).queue_tree_add(p, logger),
            "router.mikrotik.queue.tree.edit":      lambda p, logger: RouterOSQueuesDriver(d).queue_tree_edit(p, logger),
            "router.mikrotik.queue.tree.delete":    lambda p, logger: RouterOSQueuesDriver(d).queue_tree_delete(p, logger),
            "router.mikrotik.queue.tree.enable":    lambda p, logger: RouterOSQueuesDriver(d).queue_tree_enable(p, logger),
            "router.mikrotik.queue.tree.disable":   lambda p, logger: RouterOSQueuesDriver(d).queue_tree_disable(p, logger),
            "router.mikrotik.queue.type.list":      lambda p, logger: RouterOSQueuesDriver(d).queue_type_list(p, logger),
            "router.mikrotik.queue.type.add":       lambda p, logger: RouterOSQueuesDriver(d).queue_type_add(p, logger),
            "router.mikrotik.queue.type.edit":      lambda p, logger: RouterOSQueuesDriver(d).queue_type_edit(p, logger),
            "router.mikrotik.queue.type.delete":    lambda p, logger: RouterOSQueuesDriver(d).queue_type_delete(p, logger),

            # Firewall Management
            "router.mikrotik.fw.filter.add":       lambda p, logger: RouterOSFirewallDriver(d).filter_add(p, logger),
            "router.mikrotik.fw.filter.edit":      lambda p, logger: RouterOSFirewallDriver(d).filter_edit(p, logger),
            "router.mikrotik.fw.filter.delete":    lambda p, logger: RouterOSFirewallDriver(d).filter_delete(p, logger),
            "router.mikrotik.fw.filter.enable":    lambda p, logger: RouterOSFirewallDriver(d).filter_enable(p, logger),
            "router.mikrotik.fw.filter.disable":   lambda p, logger: RouterOSFirewallDriver(d).filter_disable(p, logger),
            "router.mikrotik.fw.filter.list":      lambda p, logger: RouterOSFirewallDriver(d).filter_list(p, logger),
            "router.mikrotik.fw.nat.add":          lambda p, logger: RouterOSFirewallDriver(d).nat_add(p, logger),
            "router.mikrotik.fw.nat.edit":         lambda p, logger: RouterOSFirewallDriver(d).nat_edit(p, logger),
            "router.mikrotik.fw.nat.delete":       lambda p, logger: RouterOSFirewallDriver(d).nat_delete(p, logger),
            "router.mikrotik.fw.nat.enable":       lambda p, logger: RouterOSFirewallDriver(d).nat_enable(p, logger),
            "router.mikrotik.fw.nat.disable":      lambda p, logger: RouterOSFirewallDriver(d).nat_disable(p, logger),
            "router.mikrotik.fw.nat.list":         lambda p, logger: RouterOSFirewallDriver(d).nat_list(p, logger),
            "router.mikrotik.fw.mangle.add":       lambda p, logger: RouterOSFirewallDriver(d).mangle_add(p, logger),
            "router.mikrotik.fw.mangle.edit":      lambda p, logger: RouterOSFirewallDriver(d).mangle_edit(p, logger),
            "router.mikrotik.fw.mangle.delete":    lambda p, logger: RouterOSFirewallDriver(d).mangle_delete(p, logger),
            "router.mikrotik.fw.mangle.enable":    lambda p, logger: RouterOSFirewallDriver(d).mangle_enable(p, logger),
            "router.mikrotik.fw.mangle.disable":   lambda p, logger: RouterOSFirewallDriver(d).mangle_disable(p, logger),
            "router.mikrotik.fw.mangle.list":      lambda p, logger: RouterOSFirewallDriver(d).mangle_list(p, logger),
            "router.mikrotik.fw.raw.add":          lambda p, logger: RouterOSFirewallDriver(d).raw_add(p, logger),
            "router.mikrotik.fw.raw.edit":         lambda p, logger: RouterOSFirewallDriver(d).raw_edit(p, logger),
            "router.mikrotik.fw.raw.delete":       lambda p, logger: RouterOSFirewallDriver(d).raw_delete(p, logger),
            "router.mikrotik.fw.raw.enable":       lambda p, logger: RouterOSFirewallDriver(d).raw_enable(p, logger),
            "router.mikrotik.fw.raw.disable":      lambda p, logger: RouterOSFirewallDriver(d).raw_disable(p, logger),
            "router.mikrotik.fw.raw.list":         lambda p, logger: RouterOSFirewallDriver(d).raw_list(p, logger),
            "router.mikrotik.fw.service-port.list":    lambda p,logger: RouterOSFirewallDriver(d).service_port_list(p, logger),
            "router.mikrotik.fw.service-port.edit":    lambda p,logger: RouterOSFirewallDriver(d).service_port_edit(p, logger),
            "router.mikrotik.fw.service-port.enable":  lambda p,logger: RouterOSFirewallDriver(d).service_port_enable(p, logger),
            "router.mikrotik.fw.service-port.disable": lambda p,logger: RouterOSFirewallDriver(d).service_port_disable(p, logger),
            "router.mikrotik.fw.conn.list":      lambda p, logger: RouterOSFirewallDriver(d).conn_list(p, logger),
            "router.mikrotik.fw.conn.delete":    lambda p, logger: RouterOSFirewallDriver(d).conn_delete(p, logger),
            "router.mikrotik.fw.addr.add":      lambda p, logger: RouterOSFirewallDriver(d).addrlist_add(p, logger),
            "router.mikrotik.fw.addr.edit":     lambda p, logger: RouterOSFirewallDriver(d).addrlist_edit(p, logger),
            "router.mikrotik.fw.addr.delete":   lambda p, logger: RouterOSFirewallDriver(d).addrlist_delete(p, logger),
            "router.mikrotik.fw.addr.enable":   lambda p, logger: RouterOSFirewallDriver(d).addrlist_enable(p, logger),
            "router.mikrotik.fw.addr.disable":  lambda p, logger: RouterOSFirewallDriver(d).addrlist_disable(p, logger),
            "router.mikrotik.fw.addr.list":     lambda p, logger: RouterOSFirewallDriver(d).addrlist_list(p, logger),
            "router.mikrotik.fw.l7.add":        lambda p, logger: RouterOSFirewallDriver(d).layer7_add(p, logger),
            "router.mikrotik.fw.l7.edit":       lambda p, logger: RouterOSFirewallDriver(d).layer7_edit(p, logger),
            "router.mikrotik.fw.l7.delete":     lambda p, logger: RouterOSFirewallDriver(d).layer7_delete(p, logger),
            "router.mikrotik.fw.l7.list":       lambda p, logger: RouterOSFirewallDriver(d).layer7_list(p, logger),

            # Netwatch Management
            "router.mikrotik.nw.add":     lambda p, logger: RouterOSNetwatchDriver(d).netwatch_add(p, logger),
            "router.mikrotik.nw.edit":    lambda p, logger: RouterOSNetwatchDriver(d).netwatch_edit(p, logger),
            "router.mikrotik.nw.delete":  lambda p, logger: RouterOSNetwatchDriver(d).netwatch_delete(p, logger),
            "router.mikrotik.nw.enable":  lambda p, logger: RouterOSNetwatchDriver(d).netwatch_enable(p, logger),
            "router.mikrotik.nw.disable": lambda p, logger: RouterOSNetwatchDriver(d).netwatch_disable(p, logger),
            "router.mikrotik.nw.list":    lambda p, logger: RouterOSNetwatchDriver(d).netwatch_list(p, logger),

            # Logging Management
            "router.mikrotik.logging.action.list":    lambda p, logger: RouterOSLoggingDriver(d).action_list(p, logger),
            "router.mikrotik.logging.action.add":     lambda p, logger: RouterOSLoggingDriver(d).action_add(p, logger),
            "router.mikrotik.logging.action.edit":    lambda p, logger: RouterOSLoggingDriver(d).action_edit(p, logger),
            "router.mikrotik.logging.action.delete":  lambda p, logger: RouterOSLoggingDriver(d).action_delete(p, logger),
            "router.mikrotik.logging.rule.list":      lambda p, logger: RouterOSLoggingDriver(d).rule_list(p, logger),
            "router.mikrotik.logging.rule.add":       lambda p, logger: RouterOSLoggingDriver(d).rule_add(p, logger),
            "router.mikrotik.logging.rule.edit":      lambda p, logger: RouterOSLoggingDriver(d).rule_edit(p, logger),
            "router.mikrotik.logging.rule.delete":    lambda p, logger: RouterOSLoggingDriver(d).rule_delete(p, logger),
            "router.mikrotik.logging.rule.enable":    lambda p, logger: RouterOSLoggingDriver(d).rule_enable(p, logger),
            "router.mikrotik.logging.rule.disable":   lambda p, logger: RouterOSLoggingDriver(d).rule_disable(p, logger),

            # Identity / Routing
            "router.mikrotik.identity.set": lambda p, logger: d.set_identity(p),
        }
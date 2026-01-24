from drivers.access_point_drivers.mikrotik.ip_address import MikroTikAPIpDriver
from drivers.access_point_drivers.mikrotik.interface import MikroTikAPInterfaceDriver
from drivers.access_point_drivers.mikrotik.vlan import MikroTikAPVlanDriver
from drivers.access_point_drivers.mikrotik.dhcp_server import MikroTikAPDhcpServerDriver
from drivers.access_point_drivers.mikrotik.dhcp_client import MikroTikAPDhcpClientDriver
from drivers.access_point_drivers.mikrotik.ip_pool import MikroTikAPIpPoolDriver
from drivers.access_point_drivers.mikrotik.dns_server import MikroTikAPDnsDriver
from drivers.access_point_drivers.mikrotik.neighbor import MikroTikAPNeighborDriver
from drivers.access_point_drivers.mikrotik.snmp import MikroTikAPSNMPDriver
from drivers.access_point_drivers.mikrotik.route import MikroTikAPRouteDriver
from drivers.access_point_drivers.mikrotik.users_manager import MikroTikAPUserManagerDriver
from drivers.access_point_drivers.mikrotik.queues import MikroTikAPQueuesDriver
from drivers.access_point_drivers.mikrotik.firewall import MikroTikAPFirewallDriver
from drivers.access_point_drivers.mikrotik.netwatch import MikroTikAPNetwatchDriver
from drivers.access_point_drivers.mikrotik.logging import MikroTikAPLoggingDriver
from drivers.access_point_drivers.mikrotik.reset import MikroTikAPResetDriver
from drivers.access_point_drivers.mikrotik.bridge import MikroTikAPBridgeDriver

# Wireless Drivers
from drivers.access_point_drivers.mikrotik.wireless.interface import MikroTikAPWirelessInterfaceDriver
from drivers.access_point_drivers.mikrotik.wireless.wireless_scan import MikroTikAPWirelessScan
from drivers.access_point_drivers.mikrotik.wireless.registration import MikroTikAPWirelessRegistrationDriver
from drivers.access_point_drivers.mikrotik.wireless.security_profiles import MikroTikAPWirelessSecurityDriver

# SNMP File Manager
from drivers.snmp_file_manager import SNMPFileManager

class MikrotikAPActions:
    @staticmethod
    def get_actions(d):

        return {
            # Wireless Interface Management
            "ap.mikrotik.wireless.interface.list": lambda p, logger: MikroTikAPWirelessInterfaceDriver(d).list(p, logger),
            "ap.mikrotik.wireless.interface.enable": lambda p, logger: MikroTikAPWirelessInterfaceDriver(d).enable(p, logger),
            "ap.mikrotik.wireless.interface.disable": lambda p, logger: MikroTikAPWirelessInterfaceDriver(d).disable(p, logger),
            "ap.mikrotik.wireless.interface.add": lambda p, logger: MikroTikAPWirelessInterfaceDriver(d).add_interface(p, logger),
            "ap.mikrotik.wireless.interface.edit": lambda p, logger: MikroTikAPWirelessInterfaceDriver(d).edit_interface(p, logger),
            "ap.mikrotik.wireless.interface.delete": lambda p, logger: MikroTikAPWirelessInterfaceDriver(d).delete_interface(p, logger),
            "ap.mikrotik.wireless.interface.parameters": lambda p, logger: MikroTikAPWirelessInterfaceDriver(d).get_available_parameters(p, logger),

            # Wireless Security Profiles
            "ap.mikrotik.wireless.security_profile.list": lambda p, logger: MikroTikAPWirelessSecurityDriver(d).list(p, logger),
            "ap.mikrotik.wireless.security_profile.add": lambda p, logger: MikroTikAPWirelessSecurityDriver(d).add_profile(p, logger),
            "ap.mikrotik.wireless.security_profile.edit": lambda p, logger: MikroTikAPWirelessSecurityDriver(d).edit_profile(p, logger),
            "ap.mikrotik.wireless.security_profile.delete": lambda p, logger: MikroTikAPWirelessSecurityDriver(d).delete_profile(p, logger),

            # Wireless Registration Table
            "ap.mikrotik.wireless.registration.list": lambda p, logger: MikroTikAPWirelessRegistrationDriver(d).registration_list(p, logger),
            "ap.mikrotik.wireless.registration.reset": lambda p, logger: MikroTikAPWirelessRegistrationDriver(d).reset(p, logger),
            "ap.mikrotik.wireless.registration.client_details": lambda p, logger: MikroTikAPWirelessRegistrationDriver(d).get_client_details(p, logger),
            "ap.mikrotik.wireless.registration.interface_clients": lambda p, logger: MikroTikAPWirelessRegistrationDriver(d).get_interface_clients(p, logger),

            # Reset / Backup / Reboot
            "ap.mikrotik.reset.backup": lambda p, logger: MikroTikAPResetDriver(d).backup_configuration(p, logger),
            "ap.mikrotik.reset.restore": lambda p, logger: MikroTikAPResetDriver(d).restore_configuration(p, logger),
            "ap.mikrotik.reset.export": lambda p, logger: MikroTikAPResetDriver(d).export_configuration(p, logger),
            "ap.mikrotik.reset.execute": lambda p, logger: MikroTikAPResetDriver(d).reset_configuration(p, logger),
            "ap.mikrotik.reset.reboot": lambda p, logger: MikroTikAPResetDriver(d).reboot_device(p, logger),
            "ap.mikrotik.reset.list_backups": lambda p, logger: MikroTikAPResetDriver(d).list_backups(p, logger),
            "ap.mikrotik.reset.delete_backup": lambda p, logger: MikroTikAPResetDriver(d).delete_backup(p, logger),
            "ap.mikrotik.reset.get_form": lambda p, logger: MikroTikAPResetDriver(d).get_reset_options_form(p, logger),
            "ap.mikrotik.reset.factory": lambda p, logger: MikroTikAPResetDriver(d).factory_reset(p, logger),

            # Wireless Scan
            "ap.mikrotik.wireless.scan": lambda p, logger: MikroTikAPWirelessScan.scan(d, p, logger),

            # IP Address Management
            "ap.mikrotik.ip.address.add": lambda p, logger: MikroTikAPIpDriver(d).add_address(p, logger),
            "ap.mikrotik.ip.address.delete": lambda p, logger: MikroTikAPIpDriver(d).remove_address(p, logger),
            "ap.mikrotik.ip.address.edit": lambda p, logger: MikroTikAPIpDriver(d).edit_address(p, logger),
            "ap.mikrotik.ip.address.disable": lambda p, logger: MikroTikAPIpDriver(d).disable_address(p, logger),
            "ap.mikrotik.ip.address.enable": lambda p, logger: MikroTikAPIpDriver(d).enable_address(p, logger),
            "ap.mikrotik.ip.address.comment": lambda p, logger: MikroTikAPIpDriver(d).comment_address(p, logger),
            "ap.mikrotik.ip.address.list": lambda p, logger: MikroTikAPIpDriver(d).list_addresses(p, logger),

            # IP Address Management
            "ap.mikrotik.ip.address.add": lambda p, logger: MikroTikAPIpDriver(d).add_address(p, logger),
            "ap.mikrotik.ip.address.delete": lambda p, logger: MikroTikAPIpDriver(d).remove_address(p, logger),
            "ap.mikrotik.ip.address.edit": lambda p, logger: MikroTikAPIpDriver(d).edit_address(p, logger),
            "ap.mikrotik.ip.address.disable": lambda p, logger: MikroTikAPIpDriver(d).disable_address(p, logger),
            "ap.mikrotik.ip.address.enable": lambda p, logger: MikroTikAPIpDriver(d).enable_address(p, logger),
            "ap.mikrotik.ip.address.comment": lambda p, logger: MikroTikAPIpDriver(d).comment_address(p, logger),
            "ap.mikrotik.ip.address.list": lambda p, logger: MikroTikAPIpDriver(d).list_addresses(p, logger),

            # IP POOL Management
            "ap.mikrotik.ip.pool.add": lambda p, logger: MikroTikAPIpPoolDriver(d).add_pool(p, logger),
            "ap.mikrotik.ip.pool.edit": lambda p, logger: MikroTikAPIpPoolDriver(d).edit_pool(p, logger),
            "ap.mikrotik.ip.pool.delete": lambda p, logger: MikroTikAPIpPoolDriver(d).delete_pool(p, logger),
            "ap.mikrotik.ip.pool.comment": lambda p, logger: MikroTikAPIpPoolDriver(d).comment_pool(p, logger),
            "ap.mikrotik.ip.pool.list": lambda p, logger: MikroTikAPIpPoolDriver(d).list_pool(p, logger),

            # Interface Management
            "ap.mikrotik.interface.edit": lambda p, logger: MikroTikAPInterfaceDriver(d).edit_interface(p, logger),
            "ap.mikrotik.interface.disable": lambda p, logger: MikroTikAPInterfaceDriver(d).disable_interface(p, logger),
            "ap.mikrotik.interface.enable": lambda p, logger: MikroTikAPInterfaceDriver(d).enable_interface(p, logger),
            "ap.mikrotik.interface.comment": lambda p, logger: MikroTikAPInterfaceDriver(d).comment_interface(p, logger),
            "ap.mikrotik.interface.cable_test": lambda p, logger: MikroTikAPInterfaceDriver(d).cable_test(p, logger),
            "ap.mikrotik.interface.list": lambda p, logger: MikroTikAPInterfaceDriver(d).list_interface(p, logger),

            # Bridge Management
            "ap.mikrotik.bridge.add": lambda p, logger: MikroTikAPBridgeDriver(d).add_bridge(p, logger),
            "ap.mikrotik.bridge.edit": lambda p, logger: MikroTikAPBridgeDriver(d).edit_bridge(p, logger),
            "ap.mikrotik.bridge.enable": lambda p, logger: MikroTikAPBridgeDriver(d).enable_bridge(p, logger),
            "ap.mikrotik.bridge.disable": lambda p, logger: MikroTikAPBridgeDriver(d).disable_bridge(p, logger),
            "ap.mikrotik.bridge.delete": lambda p, logger: MikroTikAPBridgeDriver(d).delete_bridge(p, logger),
            "ap.mikrotik.bridge.list": lambda p, logger: MikroTikAPBridgeDriver(d).list_bridge(p, logger),
            "ap.mikrotik.bridge.port.add":     lambda p, logger: MikroTikAPBridgeDriver(d).add_port(p, logger),
            "ap.mikrotik.bridge.port.edit":    lambda p, logger: MikroTikAPBridgeDriver(d).edit_port(p, logger),
            "ap.mikrotik.bridge.port.enable":  lambda p, logger: MikroTikAPBridgeDriver(d).enable_port(p, logger),
            "ap.mikrotik.bridge.port.disable": lambda p, logger: MikroTikAPBridgeDriver(d).disable_port(p, logger),
            "ap.mikrotik.bridge.port.delete":  lambda p, logger: MikroTikAPBridgeDriver(d).delete_port(p, logger),
            "ap.mikrotik.bridge.port.list":    lambda p, logger: MikroTikAPBridgeDriver(d).list_ports(p, logger),
            "ap.mikrotik.bridge.vlan.add":     lambda p, logger: MikroTikAPBridgeDriver(d).add_vlan(p, logger),
            "ap.mikrotik.bridge.vlan.edit":    lambda p, logger: MikroTikAPBridgeDriver(d).edit_vlan(p, logger),
            "ap.mikrotik.bridge.vlan.enable":  lambda p, logger: MikroTikAPBridgeDriver(d).enable_vlan(p, logger),
            "ap.mikrotik.bridge.vlan.disable": lambda p, logger: MikroTikAPBridgeDriver(d).disable_vlan(p, logger),
            "ap.mikrotik.bridge.vlan.delete":  lambda p, logger: MikroTikAPBridgeDriver(d).delete_vlan(p, logger),
            "ap.mikrotik.bridge.vlan.list":    lambda p, logger: MikroTikAPBridgeDriver(d).vlan_list(p, logger),
            "ap.mikrotik.bridge.vlan.mvrp.list":    lambda p, logger: MikroTikAPBridgeDriver(d).mvrp_list(p, logger),

            # VLAN Management
            "ap.mikrotik.vlan.add": lambda p, logger: MikroTikAPVlanDriver(d).add_vlan(p, logger),
            "ap.mikrotik.vlan.edit": lambda p, logger: MikroTikAPVlanDriver(d).edit_vlan(p, logger),
            "ap.mikrotik.vlan.delete": lambda p, logger: MikroTikAPVlanDriver(d).delete_vlan(p, logger),
            "ap.mikrotik.vlan.enable": lambda p, logger: MikroTikAPVlanDriver(d).enable_vlan(p, logger),
            "ap.mikrotik.vlan.disable": lambda p, logger: MikroTikAPVlanDriver(d).disable_vlan(p, logger),
            "ap.mikrotik.vlan.comment": lambda p, logger: MikroTikAPVlanDriver(d).comment_vlan(p, logger),

            # DHCP SERVER
            "ap.mikrotik.dhcp.server.add": lambda p, logger: MikroTikAPDhcpServerDriver(d).add_server(p, logger),
            "ap.mikrotik.dhcp.server.edit": lambda p, logger: MikroTikAPDhcpServerDriver(d).edit_server(p, logger),
            "ap.mikrotik.dhcp.server.enable": lambda p, logger: MikroTikAPDhcpServerDriver(d).enable_server(p, logger),
            "ap.mikrotik.dhcp.server.disable": lambda p, logger: MikroTikAPDhcpServerDriver(d).disable_server(p, logger),
            "ap.mikrotik.dhcp.server.delete": lambda p, logger: MikroTikAPDhcpServerDriver(d).delete_server(p, logger),
            "ap.mikrotik.dhcp.server.list": lambda p, logger: MikroTikAPDhcpServerDriver(d).list_servers(p, logger),
            "ap.mikrotik.dhcp.network.edit": lambda p, logger: MikroTikAPDhcpServerDriver(d).edit_network(p, logger),
            "ap.mikrotik.dhcp.network.list": lambda p, logger: MikroTikAPDhcpServerDriver(d).list_networks(p, logger),
            "ap.mikrotik.dhcp.lease.list": lambda p, logger: MikroTikAPDhcpServerDriver(d).list_leases(p, logger),

            # DHCP CLIENT
            "ap.mikrotik.dhcp.client.add": lambda p, logger: MikroTikAPDhcpClientDriver(d).add_client(p, logger),
            "ap.mikrotik.dhcp.client.edit": lambda p, logger: MikroTikAPDhcpClientDriver(d).edit_client(p, logger),
            "ap.mikrotik.dhcp.client.enable": lambda p, logger: MikroTikAPDhcpClientDriver(d).enable_client(p, logger),
            "ap.mikrotik.dhcp.client.disable": lambda p, logger: MikroTikAPDhcpClientDriver(d).disable_client(p, logger),
            "ap.mikrotik.dhcp.client.delete": lambda p, logger: MikroTikAPDhcpClientDriver(d).delete_client(p, logger),
            "ap.mikrotik.dhcp.client.comment": lambda p, logger: MikroTikAPDhcpClientDriver(d).comment_client(p, logger),
            "ap.mikrotik.dhcp.client.list": lambda p, logger: MikroTikAPDhcpClientDriver(d).list_client(p, logger),

            # DNS Configuration
            "ap.mikrotik.dns.edit": lambda p, logger: MikroTikAPDnsDriver(d).edit_dns(p, logger),
            "ap.mikrotik.dns.flush": lambda p, logger: MikroTikAPDnsDriver(d).flush_cache(p, logger),
            "ap.mikrotik.dns.static.add": lambda p, logger: MikroTikAPDnsDriver(d).add_static(p, logger),
            "ap.mikrotik.dns.static.edit": lambda p, logger: MikroTikAPDnsDriver(d).edit_static(p, logger),
            "ap.mikrotik.dns.static.enable": lambda p, logger: MikroTikAPDnsDriver(d).enable_static(p, logger),
            "ap.mikrotik.dns.static.disable": lambda p, logger: MikroTikAPDnsDriver(d).disable_static(p, logger),
            "ap.mikrotik.dns.static.comment": lambda p, logger: MikroTikAPDnsDriver(d).comment_static(p, logger),
            "ap.mikrotik.dns.static.delete": lambda p, logger: MikroTikAPDnsDriver(d).delete_static(p, logger),
            "ap.mikrotik.dns.static.list": lambda p, logger: MikroTikAPDnsDriver(d).list_static(p, logger),

            # Neighbor
            "ap.mikrotik.neighbor.get": lambda p, logger: MikroTikAPNeighborDriver(d).get_neighbors(p, logger),
            "ap.mikrotik.neighbor.discovery.get": lambda p, logger: MikroTikAPNeighborDriver(d).get_discovery_settings(p, logger),
            "ap.mikrotik.neighbor.discovery.edit": lambda p, logger: MikroTikAPNeighborDriver(d).edit_discovery_settings(p, logger),

            # SNMP MikroTikAP native config
            "ap.mikrotik.snmp.config.get": lambda p, logger: MikroTikAPSNMPDriver(d).get_snmp_config(p, logger),
            "ap.mikrotik.snmp.config.edit": lambda p, logger: MikroTikAPSNMPDriver(d).edit_snmp_config(p, logger),
            "ap.mikrotik.snmp.community.list": lambda p, logger: MikroTikAPSNMPDriver(d).list_communities(p, logger),
            "ap.mikrotik.snmp.community.add": lambda p, logger: MikroTikAPSNMPDriver(d).add_community(p, logger),
            "ap.mikrotik.snmp.community.edit": lambda p, logger: MikroTikAPSNMPDriver(d).edit_community(p, logger),
            "ap.mikrotik.snmp.community.delete": lambda p, logger: MikroTikAPSNMPDriver(d).delete_community(p, logger),
            "ap.mikrotik.snmp.community.enable": lambda p, logger: MikroTikAPSNMPDriver(d).enable_community(p, logger),
            "ap.mikrotik.snmp.community.disable": lambda p, logger: MikroTikAPSNMPDriver(d).disable_community(p, logger),
            "ap.mikrotik.snmp.device.add": lambda p, logger: SNMPFileManager().add_device(p),

            # Route Management
            "ap.mikrotik.route.list": lambda p, logger: MikroTikAPRouteDriver(d).list_routes(p, logger),
            "ap.mikrotik.route.add": lambda p, logger: MikroTikAPRouteDriver(d).add_route(p, logger),
            "ap.mikrotik.route.edit": lambda p, logger: MikroTikAPRouteDriver(d).edit_route(p, logger),
            "ap.mikrotik.route.delete": lambda p, logger: MikroTikAPRouteDriver(d).delete_route(p, logger),
            "ap.mikrotik.route.disable": lambda p, logger: MikroTikAPRouteDriver(d).disable_route(p, logger),
            "ap.mikrotik.route.enable": lambda p, logger: MikroTikAPRouteDriver(d).enable_route(p, logger),
            "ap.mikrotik.route.comment": lambda p, logger: MikroTikAPRouteDriver(d).enable_route(p, logger),

            # Users Management
            "ap.mikrotik.user.list":     lambda p, logger: MikroTikAPUserManagerDriver(d).user_list(p, logger),
            "ap.mikrotik.user.add":      lambda p, logger: MikroTikAPUserManagerDriver(d).user_add(p, logger),
            "ap.mikrotik.user.edit":     lambda p, logger: MikroTikAPUserManagerDriver(d).user_edit(p, logger),
            "ap.mikrotik.user.delete":   lambda p, logger: MikroTikAPUserManagerDriver(d).user_delete(p, logger),
            "ap.mikrotik.user.enable":   lambda p, logger: MikroTikAPUserManagerDriver(d).user_enable(p, logger),
            "ap.mikrotik.user.disable":  lambda p, logger: MikroTikAPUserManagerDriver(d).user_disable(p, logger),
            "ap.mikrotik.user.comment":  lambda p, logger: MikroTikAPUserManagerDriver(d).user_comment(p, logger),
            "ap.mikrotik.group.list":    lambda p, logger: MikroTikAPUserManagerDriver(d).group_list(p, logger),
            "ap.mikrotik.group.add":     lambda p, logger: MikroTikAPUserManagerDriver(d).group_add(p, logger),
            "ap.mikrotik.group.edit":    lambda p, logger: MikroTikAPUserManagerDriver(d).group_edit(p, logger),
            "ap.mikrotik.group.delete":  lambda p, logger: MikroTikAPUserManagerDriver(d).group_delete(p, logger),
            "ap.mikrotik.group.comment": lambda p, logger: MikroTikAPUserManagerDriver(d).group_comment(p, logger),
            "ap.mikrotik.active.list":   lambda p, logger: MikroTikAPUserManagerDriver(d).active_list(p, logger),
            "ap.mikrotik.active.logout":   lambda p, logger: MikroTikAPUserManagerDriver(d).active_logout(p, logger),

            # Queues Management
            "ap.mikrotik.queue.simple.list":    lambda p, logger: MikroTikAPQueuesDriver(d).queue_simple_list(p, logger),
            "ap.mikrotik.queue.simple.add":     lambda p, logger: MikroTikAPQueuesDriver(d).queue_simple_add(p, logger),
            "ap.mikrotik.queue.simple.edit":    lambda p, logger: MikroTikAPQueuesDriver(d).queue_simple_edit(p, logger),
            "ap.mikrotik.queue.simple.delete":  lambda p, logger: MikroTikAPQueuesDriver(d).queue_simple_delete(p, logger),
            "ap.mikrotik.queue.simple.enable":  lambda p, logger: MikroTikAPQueuesDriver(d).queue_simple_enable(p, logger),
            "ap.mikrotik.queue.simple.disable": lambda p, logger: MikroTikAPQueuesDriver(d).queue_simple_disable(p, logger),
            "ap.mikrotik.queue.interface.list": lambda p, logger: MikroTikAPQueuesDriver(d).queue_interface_list(p, logger),
            "ap.mikrotik.queue.interface.edit": lambda p, logger: MikroTikAPQueuesDriver(d).queue_interface_edit(p, logger),
            "ap.mikrotik.queue.tree.list":      lambda p, logger: MikroTikAPQueuesDriver(d).queue_tree_list(p, logger),
            "ap.mikrotik.queue.tree.add":       lambda p, logger: MikroTikAPQueuesDriver(d).queue_tree_add(p, logger),
            "ap.mikrotik.queue.tree.edit":      lambda p, logger: MikroTikAPQueuesDriver(d).queue_tree_edit(p, logger),
            "ap.mikrotik.queue.tree.delete":    lambda p, logger: MikroTikAPQueuesDriver(d).queue_tree_delete(p, logger),
            "ap.mikrotik.queue.tree.enable":    lambda p, logger: MikroTikAPQueuesDriver(d).queue_tree_enable(p, logger),
            "ap.mikrotik.queue.tree.disable":   lambda p, logger: MikroTikAPQueuesDriver(d).queue_tree_disable(p, logger),
            "ap.mikrotik.queue.type.list":      lambda p, logger: MikroTikAPQueuesDriver(d).queue_type_list(p, logger),
            "ap.mikrotik.queue.type.add":       lambda p, logger: MikroTikAPQueuesDriver(d).queue_type_add(p, logger),
            "ap.mikrotik.queue.type.edit":      lambda p, logger: MikroTikAPQueuesDriver(d).queue_type_edit(p, logger),
            "ap.mikrotik.queue.type.delete":    lambda p, logger: MikroTikAPQueuesDriver(d).queue_type_delete(p, logger),

            # Firewall Management
            "ap.mikrotik.fw.filter.add":       lambda p, logger: MikroTikAPFirewallDriver(d).filter_add(p, logger),
            "ap.mikrotik.fw.filter.edit":      lambda p, logger: MikroTikAPFirewallDriver(d).filter_edit(p, logger),
            "ap.mikrotik.fw.filter.delete":    lambda p, logger: MikroTikAPFirewallDriver(d).filter_delete(p, logger),
            "ap.mikrotik.fw.filter.enable":    lambda p, logger: MikroTikAPFirewallDriver(d).filter_enable(p, logger),
            "ap.mikrotik.fw.filter.disable":   lambda p, logger: MikroTikAPFirewallDriver(d).filter_disable(p, logger),
            "ap.mikrotik.fw.filter.list":      lambda p, logger: MikroTikAPFirewallDriver(d).filter_list(p, logger),
            "ap.mikrotik.fw.nat.add":          lambda p, logger: MikroTikAPFirewallDriver(d).nat_add(p, logger),
            "ap.mikrotik.fw.nat.edit":         lambda p, logger: MikroTikAPFirewallDriver(d).nat_edit(p, logger),
            "ap.mikrotik.fw.nat.delete":       lambda p, logger: MikroTikAPFirewallDriver(d).nat_delete(p, logger),
            "ap.mikrotik.fw.nat.enable":       lambda p, logger: MikroTikAPFirewallDriver(d).nat_enable(p, logger),
            "ap.mikrotik.fw.nat.disable":      lambda p, logger: MikroTikAPFirewallDriver(d).nat_disable(p, logger),
            "ap.mikrotik.fw.nat.list":         lambda p, logger: MikroTikAPFirewallDriver(d).nat_list(p, logger),
            "ap.mikrotik.fw.mangle.add":       lambda p, logger: MikroTikAPFirewallDriver(d).mangle_add(p, logger),
            "ap.mikrotik.fw.mangle.edit":      lambda p, logger: MikroTikAPFirewallDriver(d).mangle_edit(p, logger),
            "ap.mikrotik.fw.mangle.delete":    lambda p, logger: MikroTikAPFirewallDriver(d).mangle_delete(p, logger),
            "ap.mikrotik.fw.mangle.enable":    lambda p, logger: MikroTikAPFirewallDriver(d).mangle_enable(p, logger),
            "ap.mikrotik.fw.mangle.disable":   lambda p, logger: MikroTikAPFirewallDriver(d).mangle_disable(p, logger),
            "ap.mikrotik.fw.mangle.list":      lambda p, logger: MikroTikAPFirewallDriver(d).mangle_list(p, logger),
            "ap.mikrotik.fw.raw.add":          lambda p, logger: MikroTikAPFirewallDriver(d).raw_add(p, logger),
            "ap.mikrotik.fw.raw.edit":         lambda p, logger: MikroTikAPFirewallDriver(d).raw_edit(p, logger),
            "ap.mikrotik.fw.raw.delete":       lambda p, logger: MikroTikAPFirewallDriver(d).raw_delete(p, logger),
            "ap.mikrotik.fw.raw.enable":       lambda p, logger: MikroTikAPFirewallDriver(d).raw_enable(p, logger),
            "ap.mikrotik.fw.raw.disable":      lambda p, logger: MikroTikAPFirewallDriver(d).raw_disable(p, logger),
            "ap.mikrotik.fw.raw.list":         lambda p, logger: MikroTikAPFirewallDriver(d).raw_list(p, logger),
            "ap.mikrotik.fw.service-port.list":    lambda p,logger: MikroTikAPFirewallDriver(d).service_port_list(p, logger),
            "ap.mikrotik.fw.service-port.edit":    lambda p,logger: MikroTikAPFirewallDriver(d).service_port_edit(p, logger),
            "ap.mikrotik.fw.service-port.enable":  lambda p,logger: MikroTikAPFirewallDriver(d).service_port_enable(p, logger),
            "ap.mikrotik.fw.service-port.disable": lambda p,logger: MikroTikAPFirewallDriver(d).service_port_disable(p, logger),
            "ap.mikrotik.fw.conn.list":      lambda p, logger: MikroTikAPFirewallDriver(d).conn_list(p, logger),
            "ap.mikrotik.fw.conn.delete":    lambda p, logger: MikroTikAPFirewallDriver(d).conn_delete(p, logger),
            "ap.mikrotik.fw.addr.add":      lambda p, logger: MikroTikAPFirewallDriver(d).addrlist_add(p, logger),
            "ap.mikrotik.fw.addr.edit":     lambda p, logger: MikroTikAPFirewallDriver(d).addrlist_edit(p, logger),
            "ap.mikrotik.fw.addr.delete":   lambda p, logger: MikroTikAPFirewallDriver(d).addrlist_delete(p, logger),
            "ap.mikrotik.fw.addr.enable":   lambda p, logger: MikroTikAPFirewallDriver(d).addrlist_enable(p, logger),
            "ap.mikrotik.fw.addr.disable":  lambda p, logger: MikroTikAPFirewallDriver(d).addrlist_disable(p, logger),
            "ap.mikrotik.fw.addr.list":     lambda p, logger: MikroTikAPFirewallDriver(d).addrlist_list(p, logger),
            "ap.mikrotik.fw.l7.add":        lambda p, logger: MikroTikAPFirewallDriver(d).layer7_add(p, logger),
            "ap.mikrotik.fw.l7.edit":       lambda p, logger: MikroTikAPFirewallDriver(d).layer7_edit(p, logger),
            "ap.mikrotik.fw.l7.delete":     lambda p, logger: MikroTikAPFirewallDriver(d).layer7_delete(p, logger),
            "ap.mikrotik.fw.l7.list":       lambda p, logger: MikroTikAPFirewallDriver(d).layer7_list(p, logger),

            # Netwatch Management
            "ap.mikrotik.nw.add":     lambda p, logger: MikroTikAPNetwatchDriver(d).netwatch_add(p, logger),
            "ap.mikrotik.nw.edit":    lambda p, logger: MikroTikAPNetwatchDriver(d).netwatch_edit(p, logger),
            "ap.mikrotik.nw.delete":  lambda p, logger: MikroTikAPNetwatchDriver(d).netwatch_delete(p, logger),
            "ap.mikrotik.nw.enable":  lambda p, logger: MikroTikAPNetwatchDriver(d).netwatch_enable(p, logger),
            "ap.mikrotik.nw.disable": lambda p, logger: MikroTikAPNetwatchDriver(d).netwatch_disable(p, logger),
            "ap.mikrotik.nw.list":    lambda p, logger: MikroTikAPNetwatchDriver(d).netwatch_list(p, logger),

            # Logging Management
            "ap.mikrotik.logging.action.list":    lambda p, logger: MikroTikAPLoggingDriver(d).action_list(p, logger),
            "ap.mikrotik.logging.action.add":     lambda p, logger: MikroTikAPLoggingDriver(d).action_add(p, logger),
            "ap.mikrotik.logging.action.edit":    lambda p, logger: MikroTikAPLoggingDriver(d).action_edit(p, logger),
            "ap.mikrotik.logging.action.delete":  lambda p, logger: MikroTikAPLoggingDriver(d).action_delete(p, logger),
            "ap.mikrotik.logging.rule.list":      lambda p, logger: MikroTikAPLoggingDriver(d).rule_list(p, logger),
            "ap.mikrotik.logging.rule.add":       lambda p, logger: MikroTikAPLoggingDriver(d).rule_add(p, logger),
            "ap.mikrotik.logging.rule.edit":      lambda p, logger: MikroTikAPLoggingDriver(d).rule_edit(p, logger),
            "ap.mikrotik.logging.rule.delete":    lambda p, logger: MikroTikAPLoggingDriver(d).rule_delete(p, logger),
            "ap.mikrotik.logging.rule.enable":    lambda p, logger: MikroTikAPLoggingDriver(d).rule_enable(p, logger),
            "ap.mikrotik.logging.rule.disable":   lambda p, logger: MikroTikAPLoggingDriver(d).rule_disable(p, logger),

            # Identity / Routing
            "ap.mikrotik.identity.set": lambda p, logger: d.set_identity(p),
        }
from drivers.access_point_drivers.unifi.auto_discover import AutoDiscoverAPUnifi
from drivers.access_point_drivers.unifi.paramiko import UnifiParamikoDriver
from drivers.access_point_drivers.unifi.status_db import UnifiAPStatusDB
from drivers.access_point_drivers.unifi.list_sites import UnifiAPListSites
from drivers.access_point_drivers.unifi.list_clients import UnifiAPListClients
from drivers.access_point_drivers.unifi.list_settings import UnifiAPListSettings
from drivers.access_point_drivers.unifi.list_devices import UnifiAPListDevices
from drivers.access_point_drivers.unifi.admin_activity_logs import UnifiAPAdminActivityLogs
from drivers.access_point_drivers.unifi.list_network import UnifiAPListNetwork
from drivers.access_point_drivers.unifi.list_alert import UnifiAPListAlert
from drivers.access_point_drivers.unifi.list_wlan import UnifiAPListWLAN

class UnifiAccessPointGlobalActions:

    @staticmethod
    def get_actions(d):

        return {
            # ===== GLOBAL UNIFI ACTIONS =====
            "list.sites.unifi": lambda p, logger: UnifiAPListSites.run(logger),
            "list.devices.unifi": lambda p, logger: UnifiAPListDevices.run(logger),
            "list.clients.unifi": lambda p, logger: UnifiAPListClients.run(logger),
            "list.settings.unifi": lambda p, logger: UnifiAPListSettings.run(logger),
            "admin.activity.logs.unifi": lambda p, logger: UnifiAPAdminActivityLogs.run(logger),
            "list.network.unifi": lambda p, logger: UnifiAPListNetwork.run(logger),
            "list.alert.unifi": lambda p, logger: UnifiAPListAlert.run(logger),
            "list.wlan.unifi": lambda p, logger: UnifiAPListWLAN.run(logger),
        }
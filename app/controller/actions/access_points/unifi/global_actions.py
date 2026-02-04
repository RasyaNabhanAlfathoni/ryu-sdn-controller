from drivers.access_point_drivers.unifi.auto_discover import AutoDiscoverAPUnifi
from drivers.access_point_drivers.unifi.paramiko import UnifiParamikoDriver
# from drivers.access_point_drivers.unifi.status_db import UnifiAPStatusDB
from drivers.access_point_drivers.unifi.list_sites import UnifiAPListSites
from drivers.access_point_drivers.unifi.list_clients import UnifiAPListClients
from drivers.access_point_drivers.unifi.list_settings import UnifiAPListSettings
from drivers.access_point_drivers.unifi.list_devices import UnifiAPListDevices
from drivers.access_point_drivers.unifi.admin_activity_logs import UnifiAPAdminActivityLogs
from drivers.access_point_drivers.unifi.list_network import UnifiAPListNetwork
from drivers.access_point_drivers.unifi.list_alert import UnifiAPListAlert
from drivers.access_point_drivers.unifi.list_wlan import UnifiAPListWLAN
from drivers.access_point_drivers.unifi.status_controller_device import UnifiAPStatusControllerDevice

class UnifiAccessPointGlobalActions:

    @staticmethod
    def get_actions(d):

        return {
            "ap.unifi.list.sites.unifi": lambda p, logger: UnifiAPListSites.run(logger),
            "ap.unifi.list.devices.unifi": lambda p, logger: UnifiAPListDevices.run(logger),
            "ap.unifi.list.clients.unifi": lambda p, logger: UnifiAPListClients.run(logger),
            "ap.unifi.list.settings.unifi": lambda p, logger: UnifiAPListSettings.run(logger),
            "ap.unifi.admin.activity.logs.unifi": lambda p, logger: UnifiAPAdminActivityLogs.run(logger),
            "ap.unifi.list.network.unifi": lambda p, logger: UnifiAPListNetwork.run(logger),
            "ap.unifi.list.alert.unifi": lambda p, logger: UnifiAPListAlert.run(logger),
            "ap.unifi.list.wlan.unifi": lambda p, logger: UnifiAPListWLAN.run(logger),
            "ap.unifi.status.controller.device": lambda p, logger: UnifiAPStatusControllerDevice().run_global(),
        }
from drivers.access_point_drivers.unifi.auto_discover import AutoDiscoverAPUnifi
from drivers.access_point_drivers.unifi.paramiko import UnifiParamikoDriver
from drivers.access_point_drivers.unifi.reboot import UnifiAPReboot
from drivers.access_point_drivers.unifi.reset_default import UnifiAPResetDefault

class UnifiAccessPointActions:

    @staticmethod
    def get_actions(d):

        return {
            # ===== DEVICE-BASED UNIFI ACTIONS =====
            "unifi.ap.reboot": lambda p, logger: UnifiAPReboot.run(d, logger),
            "unifi.ap.reset_default": lambda p, logger: UnifiAPResetDefault.run(d, logger),
        }
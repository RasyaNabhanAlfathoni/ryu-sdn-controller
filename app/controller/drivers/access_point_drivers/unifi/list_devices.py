import requests
from drivers.access_point_drivers.unifi.paramiko import UnifiParamikoDriver

class UnifiAPListDevices:
    name = "list_devices"

    ENDPOINT = f"{UnifiParamikoDriver.UNIFI_BASE}/query_range?field=device"

    @staticmethod
    def run(logger=None):
        if logger:
            logger("[UNIFI] Fetching devices from UniFi controller")

        try:
            resp = requests.get(UnifiAPListDevices.ENDPOINT, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            devices = data.get("data", [])

            if logger:
                logger(f"[UNIFI] Found {len(devices)} devices")

            return {
                "count": len(devices),
                "devices": devices
            }

        except Exception as e:
            if logger:
                logger(f"[UNIFI] ERROR: {e}")
            raise

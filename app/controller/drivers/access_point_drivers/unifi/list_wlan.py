import requests
from drivers.access_point_drivers.unifi.paramiko import UnifiParamikoDriver

class UnifiAPListWLAN:
    name = "list.wlan"

    ENDPOINT = f"{UnifiParamikoDriver.UNIFI_BASE}/query_range?field=wlanconf"

    @staticmethod
    def run(logger=None):
        if logger:
            logger("[UNIFI] Fetching wlan from UniFi controller")

        try:
            resp = requests.get(UnifiAPListWLAN.ENDPOINT, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            wlan = data.get("data", [])

            if logger:
                logger(f"[UNIFI] Found {len(wlan)} wlan")

            return {
                "count": len(wlan),
                "wlan": wlan
            }

        except Exception as e:
            if logger:
                logger(f"[UNIFI] ERROR: {e}")
            raise

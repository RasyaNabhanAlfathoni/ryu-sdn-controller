import requests
from drivers.access_point_drivers.unifi.paramiko import UnifiParamikoDriver

class UnifiAPListSettings:
    name = "list_settings"

    ENDPOINT = f"{UnifiParamikoDriver.UNIFI_BASE}/query_range?field=setting"

    @staticmethod
    def run(logger=None):
        if logger:
            logger("[UNIFI] Fetching settings from UniFi controller")

        try:
            resp = requests.get(UnifiAPListSettings.ENDPOINT, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            settings = data.get("data", [])

            if logger:
                logger(f"[UNIFI] Found {len(settings)} settings")

            return {
                "count": len(settings),
                "settings": settings
            }

        except Exception as e:
            if logger:
                logger(f"[UNIFI] ERROR: {e}")
            raise
import requests
from drivers.access_point_drivers.unifi.paramiko import UnifiParamikoDriver

class UnifiAPListAlert:
    name = "list.alert"

    ENDPOINT = f"{UnifiParamikoDriver.UNIFI_BASE}/query_range?field=alert"

    @staticmethod
    def run(logger=None):
        if logger:
            logger("[UNIFI] Fetching alert from UniFi controller")

        try:
            resp = requests.get(UnifiAPListAlert.ENDPOINT, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            alert = data.get("data", [])

            if logger:
                logger(f"[UNIFI] Found {len(alert)} alert")

            return {
                "count": len(alert),
                "alert": alert
            }

        except Exception as e:
            if logger:
                logger(f"[UNIFI] ERROR: {e}")
            raise

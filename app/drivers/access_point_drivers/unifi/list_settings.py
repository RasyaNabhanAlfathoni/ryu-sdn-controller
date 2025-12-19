import requests

class UnifiAPListSettings:
    name = "list_settings"

    UNIFI_BASE = "http://192.168.100.85:3000"
    ENDPOINT = f"{UNIFI_BASE}/query_range?field=setting"

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

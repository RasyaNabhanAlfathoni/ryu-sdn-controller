import requests

class UnifiAPListDevices:
    name = "list_devices"

    UNIFI_BASE = "http://192.168.100.85:3000"
    ENDPOINT = f"{UNIFI_BASE}/query_range?field=device"

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

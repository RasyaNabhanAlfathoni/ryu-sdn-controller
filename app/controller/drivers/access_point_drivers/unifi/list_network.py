import requests

class UnifiAPListNetwork:
    name = "list.network"

    UNIFI_BASE = "http://10.10.10.34:3000"
    ENDPOINT = f"{UNIFI_BASE}/query_range?field=networkconf"

    @staticmethod
    def run(logger=None):
        if logger:
            logger("[UNIFI] Fetching network from UniFi controller")

        try:
            resp = requests.get(UnifiAPListNetwork.ENDPOINT, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            network = data.get("data", [])

            if logger:
                logger(f"[UNIFI] Found {len(network)} network")

            return {
                "count": len(network),
                "network": network
            }

        except Exception as e:
            if logger:
                logger(f"[UNIFI] ERROR: {e}")
            raise

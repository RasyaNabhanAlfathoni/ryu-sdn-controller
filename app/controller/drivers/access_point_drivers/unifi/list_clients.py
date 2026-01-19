import requests

class UnifiAPListClients:
    name = "list_clients"

    UNIFI_BASE = "http://10.10.10.34:3000"
    ENDPOINT = f"{UNIFI_BASE}/query_range?field=user"

    @staticmethod
    def run(logger=None):
        if logger:
            logger("[UNIFI] Fetching clients from UniFi controller")

        try:
            resp = requests.get(UnifiAPListClients.ENDPOINT, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            clients = data.get("data", [])

            if logger:
                logger(f"[UNIFI] Found {len(clients)} clients")

            return {
                "count": len(clients),
                "clients": clients
            }

        except Exception as e:
            if logger:
                logger(f"[UNIFI] ERROR: {e}")
            raise

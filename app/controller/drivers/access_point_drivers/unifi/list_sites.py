import requests

class UnifiAPListSites:
    name = "list_sites"

    UNIFI_BASE = "http://192.168.100.85:3000"
    ENDPOINT = f"{UNIFI_BASE}/query_range?field=site"

    @staticmethod
    def run(logger=None):
        if logger:
            logger("[UNIFI] Fetching sites from UniFi controller")

        try:
            resp = requests.get(UnifiAPListSites.ENDPOINT, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            sites = data.get("data", [])

            if logger:
                logger(f"[UNIFI] Found {len(sites)} sites")

            return {
                "count": len(sites),
                "sites": sites
            }

        except Exception as e:
            if logger:
                logger(f"[UNIFI] ERROR: {e}")
            raise

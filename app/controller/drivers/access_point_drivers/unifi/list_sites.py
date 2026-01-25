import requests
from drivers.access_point_drivers.unifi.paramiko import UnifiParamikoDriver

class UnifiAPListSites:
    name = "list_sites"

    ENDPOINT = f"{UnifiParamikoDriver.UNIFI_BASE}/query_range?field=site"

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
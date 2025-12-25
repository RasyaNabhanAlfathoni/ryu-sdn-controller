import requests

class UnifiAPAdminActivityLogs:
    name = "admin_activity_logs"

    UNIFI_BASE = "http://192.168.100.85:3000"
    ENDPOINT = f"{UNIFI_BASE}/query_range?field=admin_activity_log"

    @staticmethod
    def run(logger=None):
        if logger:
            logger("[UNIFI] Fetching admin activity logs from UniFi controller")

        try:
            resp = requests.get(UnifiAPAdminActivityLogs.ENDPOINT, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            admin_activity_logs = data.get("data", [])

            if logger:
                logger(f"[UNIFI] Found {len(admin_activity_logs)} admin activity logs")

            return {
                "count": len(admin_activity_logs),
                "admin_activity_logs": admin_activity_logs
            }

        except Exception as e:
            if logger:
                logger(f"[UNIFI] ERROR: {e}")
            raise
import requests
import hashlib
import subprocess
from datetime import datetime


class RuijieCloudDriver:
    name = "ruijie_cloud"

    def __init__(self, dev=None):
        self.dev = dev or {}
        self.ip = (
            self.dev.get("ip")
            or self.dev.get("main_ip_address")
        )
        self.device_id = self.dev.get("device_id")
        self.serial_number = (
            self.dev.get("serial_number")
            or self.dev.get("serial-number")
        )
        self.device_type = self.dev.get("device_type")

    BASE_URL = "https://cloud-as.ruijienetworks.com"
    ACCESS_TOKEN = "oi1w0F0p7J7op5B8L4g4J8L0oFZNpY67"

    TIMEOUT = 10
    PER_PAGE = 100

    def ping(ip):
        try:
            subprocess.check_output(
                ["ping", "-c", "2", ip],
                stderr=subprocess.DEVNULL,
                timeout=3
            )
            return True
        except:
            return False

    @staticmethod
    def now():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def generate_device_id(mac: str) -> str:
        mac = mac.lower().replace(":", "").replace(".", "")
        return "dev_" + hashlib.sha1(mac.encode()).hexdigest()[:10]

    @classmethod
    def _get(cls, path, params=None):
        params = params or {}
        params["access_token"] = cls.ACCESS_TOKEN
        url = f"{cls.BASE_URL}{path}"

        res = requests.get(url, params=params, timeout=cls.TIMEOUT)
        res.raise_for_status()
        data = res.json()

        if data.get("code") not in (0, None):
            raise RuntimeError(f"Ruijie API error: {data}")

        return data

    # ===============================
    # GROUP
    # ===============================
    @classmethod
    def fetch_groups(cls):
        return cls._get(
            "/service/api/group/single/tree",
            {"depth": "BUILDING"}
        ).get("groups", {})

    @classmethod
    def extract_buildings(cls, tree):
        out = []

        def walk(n):
            if n.get("type") == "BUILDING":
                out.append({
                    "group_id": n["groupId"],
                    "name": n["name"]
                })
            for sg in n.get("subGroups", []):
                walk(sg)

        walk(tree)
        return out

    # ===============================
    # DEVICE LOOKUP
    # ===============================
    @classmethod
    def fetch_devices(cls, group_id):
        res = cls._get(
            "/service/api/maint/devices",
            {
                "page": 1,
                "per_page": cls.PER_PAGE,
                "group_id": group_id,
            }
        )
        return res.get("deviceList", [])

    @classmethod
    def lookup_by_ip(cls, ip: str):
        tree = cls.fetch_groups()
        groups = cls.extract_buildings(tree)

        for g in groups:
            devices = cls.fetch_devices(g["group_id"])

            for d in devices:
                if d.get("localIp") == ip:
                    return cls.normalize(d, g)

        return None

    # ===============================
    # NORMALIZE
    # ===============================
    @classmethod
    def normalize(cls, d, group):
        device_id = cls.generate_device_id(d["mac"])

        return {
            "connected": True,
            "device_id": device_id,
            "identity": d.get("name"),
            "hostname": d.get("name"),
            "cloud_online_status": d.get("onlineStatus"),
            "cloud_offline_reason": d.get("offlineReason"),
            "status": "active" if d.get("onlineStatus") == "ON" else "inactive",
            "serial_number": d.get("serialNumber"),
            "vendor": "ruijie",
            "southbound": "ruijie_cloud",
            "device_type": d.get("commonType", "switch").lower(),
            "model": d.get("productClass"),
            "os_version": d.get("softwareVersion"),
            "main_ip_address": d.get("localIp"),
            "main_mac_address": d.get("mac"),
            "status": "active" if d.get("onlineStatus") == "ON" else "inactive",
            "location": group["name"],
            "external_group_id": group["group_id"],
            "last_seen": cls.now(),
        }

    def get_device_info(self):
        """
        Entry point standar untuk orchestrator
        """
        if not self.ip:
            return {
                "connected": False,
                "error": "IP address is required for Ruijie cloud lookup"
            }

        info = self.lookup_by_ip(self.ip)

        if not info:
            return {
                "connected": False,
                "error": f"Device with IP {self.ip} not found in Ruijie Cloud"
            }

        return info

    def test_connection(self):
        if not self.ip:
            return False, "No IP address"

        ping_ok = self.ping(self.ip)

        info = self.lookup_by_ip(self.ip)

        if not info:
            return False, "Device not found in Ruijie Cloud"

        cloud_status = info.get("cloud_online_status")

        cloud_online = cloud_status == "ON"

        if ping_ok and cloud_online:
            return True, "Device ACTIVE (ping OK, cloud ON)"

        if ping_ok and not cloud_online:
            return False, f"Device reachable but cloud OFF ({cloud_status})"

        if not ping_ok and cloud_online:
            return False, "Cloud ON but device not reachable locally"

        return False, "Device DOWN"

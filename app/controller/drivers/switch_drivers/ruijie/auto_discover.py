import requests
import hashlib
from datetime import datetime
from ryu.lib import hub
from drivers.snmp_file_manager import SNMPFileManager
from database.device_repository import DeviceRepository

class AutoDiscoverRuijie:
    name = "ruijie_auto_discover"

    BASE_URL = "https://cloud-as.ruijienetworks.com"
    INTERVAL = 10

    # masih hardcore
    ACCESS_TOKEN = "or1n0Q0u7r7oB5T8m4e4S8N0oJ3tcmAz"

    _snapshot = {}

    @staticmethod
    def generate_device_id(mac: str) -> str:
        mac = mac.lower().replace(".", "").replace(":", "")
        return "dev_" + hashlib.sha1(mac.encode()).hexdigest()[:10]

    @staticmethod
    def now():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def fetch_group_tree(cls):
        url = f"{cls.BASE_URL}/service/api/group/single/tree"
        params = {
            "depth": "BUILDING",
            "access_token": cls.ACCESS_TOKEN
        }
        res = requests.get(url, params=params, timeout=10).json()
        return res.get("groups", {})

    @classmethod
    def extract_building_groups(cls, tree):
        buildings = []

        def walk(node):
            if node.get("type") == "BUILDING":
                buildings.append({
                    "group_id": node["groupId"],
                    "name": node["name"],
                    "timezone": node.get("timezone")
                })

            for sg in node.get("subGroups", []):
                walk(sg)

        walk(tree)
        return buildings

    @classmethod
    def fetch_devices_by_group(cls, group_id):
        url = f"{cls.BASE_URL}/service/api/maint/devices"
        params = {
            "page": 1,
            "per_page": 100,
            "group_id": group_id,
            "product__type": "Switch",
            "access_token": cls.ACCESS_TOKEN
        }
        res = requests.get(url, params=params, timeout=10).json()
        return res.get("deviceList", [])

    @classmethod
    def normalize_device(cls, d, group):
        device_id = cls.generate_device_id(d["mac"])

        return {
            "device_id": device_id,

            # identity
            "identity": d.get("name"),
            "hostname": d.get("name"),
            "serial_number": d.get("serialNumber"),

            # system
            "model": d.get("productClass"),
            "os_version": d.get("softwareVersion"),
            "device_type": d.get("commonType").lower(),

            # network
            "main_ip_address": d.get("localIp"),
            "main_mac_address": d.get("mac"),

            # metadata
            "vendor": "ruijie",
            "southbound": "ruijie_cloud",
            "status": "active" if d.get("onlineStatus") == "ON" else "inactive",
            "location": group["name"],
            "external_group_id": group["group_id"],
            "last_seen": cls.now()
        }

    @classmethod
    def fetch_device_detail(cls, serial):
        url = f"{cls.BASE_URL}/service/api/device/{serial}"
        params = {"access_token": cls.ACCESS_TOKEN}
        res = requests.get(url, params=params, timeout=10).json()
        return res

    @classmethod
    def run(cls):
        try:
            tree = cls.fetch_group_tree()
            groups = cls.extract_building_groups(tree)

            for group in groups:
                devices = cls.fetch_devices_by_group(group["group_id"])

                for d in devices:
                    try:
                        dev = cls.normalize_device(d, group)
                        device_id = dev["device_id"] 

                        fingerprint = hashlib.sha1(
                            f"{dev['identity']}|{dev['os_version']}|{dev['main_ip_address']}".encode()
                        ).hexdigest()

                        old_fp = cls._snapshot.get(dev["device_id"])

                        existing = DeviceRepository.find_by_device_id(dev["device_id"])

                        if not existing:
                            cls._snapshot[dev["device_id"]] = fingerprint
                            print(f"[RUIJIE] INSERT {dev['identity']}")

                            DeviceRepository.insert_network_device(dev)
                            DeviceRepository.insert_switch(dev)

                            try:
                                snmp = SNMPFileManager()
                                snmp.add_device({
                                    "device_id": device_id,
                                    "ip": dev["main_ip_address"],
                                    "module": dev["vendor"].lower(),
                                    "device_name": dev["identity"],
                                    "location": dev.get("snmp_location", "Unknown"),
                                })
                                print(f"[RUIJIE-AUTO] SNMP TARGET ADDED {device_id}")

                            except Exception as e:
                                print(f"[RUIJIE-AUTO] SNMP SKIP {device_id}: {e}")

                        elif old_fp != fingerprint:
                            cls._snapshot[dev["device_id"]] = fingerprint
                            print(f"[RUIJIE] UPDATE {dev['identity']}")

                            DeviceRepository.update_network_device(
                                dev["device_id"], dev
                            )
                            DeviceRepository.update_switch(
                                dev["device_id"], dev
                            )

                        detail = cls.fetch_device_detail(dev["serial_number"])
                        status = "active" if detail.get("onlineStatus") == "ON" else "inactive"

                        DeviceRepository.update_device_status(
                            dev["device_id"],
                            status,
                            cls.now()
                        )

                    except Exception as e:
                        print(f"[RUIJIE] DEVICE ERROR {d.get('name')}: {e}")

        except Exception as e:
            print(f"[RUIJIE] RUN ERROR: {e}")

    @classmethod
    def loop(cls):
        print("[RUIJIE] Ruijie Auto Discovery started")
        while True:
            try:
                cls.run()
            except Exception as e:
                print(f"[RUIJIE] LOOP ERROR: {e}")

            hub.sleep(cls.INTERVAL)
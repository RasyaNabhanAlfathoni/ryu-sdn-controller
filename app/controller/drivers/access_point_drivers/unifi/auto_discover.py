import requests
import hashlib
from ryu.lib import hub
from database.device_repository import DeviceRepository
from drivers.snmp_file_manager import SNMPFileManager


class AutoDiscoverAPUnifi:
    name = "unifi_auto_discover"

    UNIFI_BASE = "http://192.168.100.85:3000"
    DEVICE_ENDPOINT = f"{UNIFI_BASE}/query_range?field=device"
    SETTING_ENDPOINT = f"{UNIFI_BASE}/query_range?field=setting"

    INTERVAL = 10

    # SNAPSHOT CACHE (MEMORY)
    _snapshot = {}

    # DEVICE ID (STABLE FROM MAC)
    @staticmethod
    def generate_device_id(mac: str) -> str:
        mac = mac.lower().replace(":", "")
        return "dev_" + hashlib.sha1(mac.encode()).hexdigest()[:10]

    # OPERATIONAL FINGERPRINT (NO cfgversion)
    @staticmethod
    def build_fingerprint(d: dict) -> str:
        important = [
            d.get("mac"),
            d.get("ip"),
            d.get("name"),
            d.get("model"),
            d.get("version"),
        ]
        raw = "|".join(str(x) for x in important)
        return hashlib.sha1(raw.encode()).hexdigest()

    # SSH CREDENTIAL FROM UNIFI SETTING
    @staticmethod
    def get_ssh_credential(settings: list, site_id: str):
        mgmts = [
            s for s in settings
            if s.get("key") == "mgmt"
            and s.get("site_id") == site_id
            and s.get("x_ssh_enabled") is True
        ]

        if not mgmts:
            return "ubnt", "ubnt"

        mgmt = mgmts[-1]
        return (
            mgmt.get("x_ssh_username", "ubnt"),
            mgmt.get("x_ssh_password", "ubnt")
        )

    # NORMALIZE
    @staticmethod
    def _norm(v):
        return "" if v is None else str(v).strip()

    # CHECK REAL CHANGE
    @classmethod
    def has_changed(cls, old: dict, new: dict) -> bool:
        keys = [
            "identity",
            "hostname",
            "model",
            "os_version",
            "main_ip_address",
            "username",
            "password",
        ]

        for k in keys:
            if cls._norm(old.get(k)) != cls._norm(new.get(k)):
                return True

        return False

    # MAIN DISCOVERY
    @classmethod
    def run(cls):
        try:
            devices = requests.get(
                cls.DEVICE_ENDPOINT, timeout=5
            ).json().get("data", [])

            settings = requests.get(
                cls.SETTING_ENDPOINT, timeout=5
            ).json().get("data", [])

        except Exception as e:
            print(f"[UNIFI-AUTO] API ERROR: {e}")
            return

        if not devices:
            return

        for d in devices:
            try:
                mac = d.get("mac")
                if not mac:
                    continue

                device_id = cls.generate_device_id(mac)
                fingerprint = cls.build_fingerprint(d)

                username, password = cls.get_ssh_credential(
                    settings, d.get("site_id")
                )
                
                snmp_location = d.get("snmp_location", "unknown")
                                

                dev = {
                    "device_id": device_id,

                    # identity
                    "identity": d.get("name") or "unifi-ap",
                    "hostname": d.get("name") or "unifi-ap",
                    "serial_number": d.get("external_id"), 

                    # auth
                    "username": username,
                    "password": password,

                    # version
                    "model": d.get("model"),
                    "os_version": d.get("version"),

                    # network
                    "main_ip_address": d.get("ip"),
                    "main_mac_address": mac,
                    "main_interface": "eth0",

                    # metadata
                    "vendor": "unifi",
                    "device_type": "access_point",
                    "southbound": "paramiko",
                    "status": "active",

                    # snmp
                    "snmp_location": snmp_location,
                }


                # DB EXISTENCE CHECK

                existing = DeviceRepository.find_by_device_id(device_id)

                # DB DELETED / NEW DEVICE
                if not existing:
                    cls._snapshot[device_id] = fingerprint
                    print(f"[UNIFI-AUTO] INSERT {device_id}")
                    DeviceRepository.insert_network_device(dev)
                    DeviceRepository.insert_access_point(dev)

                    try:
                        snmp = SNMPFileManager()
                        snmp.add_device({
                            "device_id": device_id,
                            "ip": dev["main_ip_address"],
                            "module": dev["vendor"].lower(),
                            "device_name": dev["identity"],
                            "location": dev.get("snmp_location", "Unknown"),
                        })
                        print(f"[UNIFI-AUTO] SNMP TARGET ADDED {device_id}")

                    except Exception as e:
                        print(f"[UNIFI-AUTO] SNMP SKIP {device_id}: {e}")

                    continue


                # SNAPSHOT CHECK
                if cls._snapshot.get(device_id) == fingerprint:
                    continue

                cls._snapshot[device_id] = fingerprint

                # UPDATE CHECK
                if cls.has_changed(existing, dev):
                    print(f"[UNIFI-AUTO] UPDATE {device_id}")
                    DeviceRepository.update_network_device(device_id, dev)
                    DeviceRepository.update_access_point(device_id, dev)

            except Exception as e:
                print(f"[UNIFI-AUTO] DEVICE ERROR {d.get('ip')}: {e}")

    # LOOP
    @classmethod
    def loop(cls):
        print("[UNIFI-AUTO] UniFi Auto Discovery started (10s interval)")
        while True:
            try:
                cls.run()
            except Exception as e:
                print(f"[UNIFI-AUTO] LOOP ERROR: {e}")

            hub.sleep(cls.INTERVAL)

import requests
from database.device_repository import DeviceRepository

class UnifiAPStatusControllerDevice:
    # HARUS DOT STYLE
    name = "status.control.device"

    UNIFI_BASE = "http://192.168.100.85:3000"
    DEVICE_ENDPOINT = f"{UNIFI_BASE}/query_range?field=device"


    # GLOBAL ACTION
    def run_global(self):
        controller_map, controller_up = self._fetch_controller_devices()

        db_devices = DeviceRepository.list_all()

        results = []
        for dev in db_devices:
            results.append(
                self._build_status(dev, controller_map, controller_up)
            )

        return results


    # INTERNAL
    def _fetch_controller_devices(self):
        try:
            resp = requests.get(self.DEVICE_ENDPOINT, timeout=5)
            data = resp.json().get("data", [])

            # map pakai external_id (serial_number)
            controller_map = {
                d["external_id"]: d
                for d in data
                if d.get("external_id")
            }

            return controller_map, True

        except Exception as e:
            print(f"[UNIFI-STATUS] Controller unreachable: {e}")
            return {}, False

    def _build_status(self, db_dev, controller_map, controller_up):
        serial = db_dev.get("serial_number")          # external_id
        mac = db_dev.get("main_mac_address")          # FIX KEY

        in_controller = bool(serial and serial in controller_map)

        if not controller_up:
            status = "CONTROLLER_DOWN"
            reason = "controller_unreachable"

        elif in_controller:
            status = "OK"
            reason = "device_present_in_both"

        else:
            status = "DB_ONLY"
            reason = "device_removed_from_controller"

        return {
            "device_id": db_dev.get("device_id"),
            "serial_number": serial,
            "mac": mac,
            "present_in_controller": in_controller,
            "present_in_database": True,
            "status": status,
            "reason": reason
        }
from drivers.switch_drivers.ruijie.device_management import RuijieDeviceManagementAPI
from drivers.switch_drivers.ruijie.ruijie_cloud import RuijieCloudDriver

class RuijieSwitchActions:
    @staticmethod
    def get_actions(d):
        api = RuijieDeviceManagementAPI(
            RuijieCloudDriver.ACCESS_TOKEN
        )

        return {
            "device.log.history.ruijie": lambda p, logger: (
                RuijieSwitchActions._log_history(api, d, p)
            )
        }

    @staticmethod
    def _log_history(api, d, p):
        if not d.serial_number:
            raise ValueError("serial_number not found on device")

        if "start_time" not in p or "end_time" not in p:
            raise ValueError("start_time and end_time are required")

        return api.get_device_history(
            sn=d.serial_number,
            log_type=p.get("log_type", "system"),
            start_time=p["start_time"],
            end_time=p["end_time"],
            page=p.get("page", 1),
            per_page=p.get("per_page", 20),
        )
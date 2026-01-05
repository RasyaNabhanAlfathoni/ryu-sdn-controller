from drivers.switch_drivers.ruijie.auto_discover import AutoDiscoverRuijie
from drivers.switch_drivers.ruijie.device_management import RuijieDeviceManagementAPI

class RuijieSwitchActions:
    @staticmethod
    def get_actions(d):
        token = AutoDiscoverRuijie.ACCESS_TOKEN

        cfg = d.config
        sn = cfg.get("serial_number") or cfg.get("serial-number")

        return {
            "device.log.history.ruijie": lambda p, logger: (
                RuijieDeviceManagementAPI(token).get_device_history(
                    sn=sn,
                    log_type=p.get("log_type"),
                    start_time=p.get("start_time"),
                    end_time=p.get("end_time"),
                    page=p.get("page"),
                    per_page=p.get("per_page")
                )
            )
        }
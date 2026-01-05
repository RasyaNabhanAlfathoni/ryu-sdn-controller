from drivers.switch_drivers.ruijie.auto_discover import AutoDiscoverRuijie

class RuijieCloudDriver:
    """Driver untuk perangkat Ruijie yang dikelola via Cloud API"""
    
    def __init__(self, config):
        self.config = config
        self.device_id = config.get("device_id")
        self.serial_number = config.get("serial_number")
        self.device_type = config.get("device_type")
        self.token = AutoDiscoverRuijie.ACCESS_TOKEN
    
    def get_device_info(self):
        """Mengembalikan informasi device (mock, karena data sudah ada dari auto-discover)"""
        return {
            "connected": True,
            "device_type": self.device_type,
            "vendor": "ruijie",
            "southbound": "ruijie_cloud",
            "serial_number": self.serial_number,
            "device_id": self.device_id
        }
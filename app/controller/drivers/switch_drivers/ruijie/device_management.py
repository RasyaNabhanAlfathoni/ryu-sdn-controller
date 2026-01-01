import requests

class RuijieDeviceManagementAPI:
    BASE_URL = "https://cloud-as.ruijienetworks.com"

    def __init__(self, access_token: str):
        self.access_token = access_token

    def list_devices(
        self,
        group_id: int,
        common_type: str,   # AP | Switch | Gateway
        page: int = 1,
        per_page: int = 10,
        key: str = None
    ):
        url = f"{self.BASE_URL}/service/api/maint/devices"
        params = {
            "access_token": self.access_token,
            "group_id": group_id,
            "common_type": common_type,
            "page": page,
            "per_page": per_page
        }

        if key is not None:
            params["key"] = key

        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()

    def get_device_status(self, sn: str):
        url = f"{self.BASE_URL}/service/api/device/{sn}"
        params = {"access_token": self.access_token}

        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()

    def get_device_flow(
        self,
        sn: str,
        start_date: int,
        end_date: int
    ):
        url = f"{self.BASE_URL}/logbizagent/logbiz/api/flow/show/hour"
        params = {"access_token": self.access_token}

        payload = {
            "sn": sn,
            "startDate": start_date,
            "endDate": end_date
        }

        res = requests.post(url, params=params, json=payload, timeout=10)
        res.raise_for_status()
        return res.json()

    def get_gateway_ports(self, sn: str):
        url = f"{self.BASE_URL}/service/api/gateway/intf/info/{sn}"
        params = {"access_token": self.access_token}

        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()

    def get_device_logs(
        self,
        sn: str,
        group_id: int,
        page: int = 1,
        per_page: int = 10,
        days: int = None
    ):
        url = f"{self.BASE_URL}/service/api/apmgt/apinfo/{sn}/devicemgtlogs"
        params = {
            "access_token": self.access_token,
            "group_id": group_id,
            "page": page,
            "per_page": per_page
        }

        if days is not None:
            params["days"] = days

        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()

    def get_device_performance(self, sn: str):
        url = f"{self.BASE_URL}/logbizagent/logbiz/api/sys/current_performance"
        params = {
            "access_token": self.access_token,
            "sn": sn
        }

        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()

    def get_switch_ports(
        self,
        sn: str,
        page_index: int = 0,
        page_size: int = 100
    ):
        url = f"{self.BASE_URL}/service/api/conf/switch/device/{sn}/ports"
        params = {
            "access_token": self.access_token,
            "page_index": page_index,
            "page_size": page_size
        }

        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()

    def get_switch_poe_ports(self, sn: str):
        url = f"{self.BASE_URL}/service/api/conf/switch/device/{sn}/poe/info"
        params = {"access_token": self.access_token}

        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()

    def get_switch_poe_power(self, sn: str):
        url = f"{self.BASE_URL}/service/api/conf/switch/device/{sn}/poe/pwr"
        params = {"access_token": self.access_token}

        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()

    def get_application_traffic(
        self,
        group_id: int,
        sn: str,
        page_index: int,
        page_size: int,
        start_time: int = None,
        end_time: int = None
    ):
        url = f"{self.BASE_URL}/logbizagent/logbiz/api/eg/appflow/statistic/data-minute/appname"
        params = {"access_token": self.access_token}

        payload = {
            "groupId": group_id,
            "sn": sn,
            "pageIndex": page_index,
            "pageSize": page_size
        }

        if start_time is not None:
            payload["startTime"] = start_time
        if end_time is not None:
            payload["endTime"] = end_time

        res = requests.post(url, params=params, json=payload, timeout=10)
        res.raise_for_status()
        return res.json()

    def get_device_history(
        self,
        sn: str,
        log_type: str,
        start_time: int,
        end_time: int,
        page: int = 1,
        per_page: int = 10
    ):
        url = f"{self.BASE_URL}/service/api/open/v1/dev/{sn}/devicemgtlogs"
        params = {
            "access_token": self.access_token,
            "log_type": log_type,
            "startTime": start_time,
            "endTime": end_time,
            "page": page,
            "per_page": per_page
        }

        res = requests.get(
            url,
            params=params,
            timeout=10
        )
        res.raise_for_status()
        return res.json()
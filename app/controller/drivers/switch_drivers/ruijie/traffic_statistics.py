import requests


class RuijieTrafficStatisticsAPI:
    BASE_URL = "https://cloud-as.ruijienetworks.com"

    def __init__(self, access_token: str):
        self.access_token = access_token

    def app_group_minute(
        self,
        group_id: int,
        sn: str,
        intf_name: str,
        start_time: int,
        end_time: int,
        size: int = 100
    ):
        url = f"{self.BASE_URL}/service/api/open/v1/dev/eg/appflow/data-minute/appgroup"
        params = {
            "access_token": self.access_token,
            "group_id": group_id,
            "sn": sn,
            "intfName": intf_name,
            "start_time": start_time,
            "end_time": end_time,
            "size": size
        }

        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()

    def app_group_day(
        self,
        group_id: int,
        sn: str,
        intf_name: str,
        start_time: int,
        end_time: int,
        size: int = 100
    ):
        url = f"{self.BASE_URL}/service/api/open/v1/dev/eg/appflow/data-day/appgroup"
        params = {
            "access_token": self.access_token,
            "group_id": group_id,
            "sn": sn,
            "intfName": intf_name,
            "start_time": start_time,
            "end_time": end_time,
            "size": size
        }

        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()


    def app_name_minute(
        self,
        group_id: int,
        sn: str,
        intf_name: str,
        start_time: int,
        end_time: int,
        page_index: int = 1,
        page_size: int = 10
    ):
        url = f"{self.BASE_URL}/service/api/open/v1/dev/eg/appflow/data-minute/appname"
        params = {"access_token": self.access_token}

        payload = {
            "groupId": group_id,
            "sn": sn,
            "intfName": intf_name,
            "startTime": start_time,
            "endTime": end_time,
            "pageIndex": page_index,
            "pageSize": page_size
        }

        res = requests.post(url, params=params, json=payload, timeout=10)
        res.raise_for_status()
        return res.json()

    def app_name_day(
        self,
        group_id: int,
        sn: str,
        intf_name: str,
        start_time: int,
        end_time: int,
        page_index: int = 1,
        page_size: int = 10
    ):
        url = f"{self.BASE_URL}/service/api/open/v1/dev/eg/appflow/data-day/appname"
        params = {"access_token": self.access_token}

        payload = {
            "groupId": group_id,
            "sn": sn,
            "intfName": intf_name,
            "startTime": start_time,
            "endTime": end_time,
            "pageIndex": page_index,
            "pageSize": page_size
        }

        res = requests.post(url, params=params, json=payload, timeout=10)
        res.raise_for_status()
        return res.json()

    def peak_rate_trend(
        self,
        sn: str,
        intf_name: str,
        start_time: int,
        end_time: int
    ):
        url = f"{self.BASE_URL}/service/api/open/v1/dev/peekflow/intf/trend"
        params = {
            "access_token": self.access_token,
            "sn": sn,
            "intf_name": intf_name,
            "start_time": start_time,
            "end_time": end_time
        }

        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()
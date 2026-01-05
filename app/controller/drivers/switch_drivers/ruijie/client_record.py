import requests

class RuijieClientRecordAPI:
    BASE_URL = "https://cloud-as.ruijienetworks.com"

    def __init__(self, access_token: str):
        self.access_token = access_token

    def get_client_records(
        self,
        group_id: int,
        page_size: int,
        page_index: int,
        sta_type: str,   # "currentUser" | "onofflineUserHistory"
        mac: str = None,
        ssid: str = None,
        sn: str = None
    ):
        url = f"{self.BASE_URL}/logbizagent/logbiz/api/sta/sta_users"
        params = {
            "access_token": self.access_token
        }

        payload = {
            "groupId": group_id,
            "pageSize": page_size,
            "pageIndex": page_index,
            "staType": sta_type
        }

        if mac is not None:
            payload["mac"] = mac
        if ssid is not None:
            payload["ssid"] = ssid
        if sn is not None:
            payload["sn"] = sn

        res = requests.post(
            url,
            params=params,
            json=payload,
            timeout=10
        )
        res.raise_for_status()
        return res.json()
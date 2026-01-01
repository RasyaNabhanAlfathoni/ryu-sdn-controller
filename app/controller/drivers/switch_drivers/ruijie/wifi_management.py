import requests


class RuijieWiFiManagementAPI:
    BASE_URL = "https://cloud-as.ruijienetworks.com"

    def __init__(self, access_token: str):
        self.access_token = access_token

    def upsert_wifi(
        self,
        group_id: int,
        wifi_grp_ssid: bool,
        wireless_conf: dict,
        ssid_id: int = None
    ):
        url = f"{self.BASE_URL}/service/api/open/v1/wifi"
        params = {
            "access_token": self.access_token
        }

        payload = {
            "groupId": group_id,
            "wifiGrpSsid": wifi_grp_ssid,
            "wirelessConfEntity": wireless_conf
        }

        # kalau ada ssidId → UPDATE
        if ssid_id is not None:
            payload["ssidId"] = ssid_id

        res = requests.post(
            url,
            params=params,
            json=payload,
            timeout=10
        )
        res.raise_for_status()
        return res.json()

import requests


class RuijieUserGroupManagementAPI:
    BASE_URL = "https://cloud-as.ruijienetworks.com"

    def __init__(self, access_token: str):
        self.access_token = access_token

    def list_user_groups(
        self,
        group_id: int,
        page_index: int = 0,
        page_size: int = 20
    ):
        url = f"{self.BASE_URL}/service/api/intl/usergroup/list/{group_id}"
        params = {
            "access_token": self.access_token,
            "pageIndex": page_index,
            "pageSize": page_size
        }

        res = requests.get(
            url,
            params=params,
            timeout=10
        )
        res.raise_for_status()
        return res.json()
import requests


class RuijieClientInformationAPI:
    BASE_URL = "https://cloud-as.ruijienetworks.com"

    def __init__(self, access_token: str):
        self.access_token = access_token

    def get_current_clients(
        self,
        group_id: list = None,
        page_index: int = None,
        page_size: int = None
    ):
        url = f"{self.BASE_URL}/service/api/open/v1/dev/user/current-user"

        params = {
            "access_token": self.access_token
        }

        # optional query params
        if group_id is not None:
            # API expects array[string]
            params["group_id"] = group_id
        if page_index is not None:
            params["page_index"] = page_index
        if page_size is not None:
            params["page_size"] = page_size

        res = requests.get(
            url,
            params=params,
            timeout=10
        )
        res.raise_for_status()
        return res.json()
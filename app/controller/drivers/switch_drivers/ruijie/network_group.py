import requests


class RuijieNetworkGroupsAPI:
    BASE_URL = "https://cloud-as.ruijienetworks.com"

    def __init__(self, access_token: str):
        self.access_token = access_token

    # LIST NETWORK GROUPS
    def list_groups(self, depth="BUILDING"):
        url = f"{self.BASE_URL}/service/api/group/single/tree"
        params = {
            "depth": depth,
            "access_token": self.access_token
        }

        print("URL:", url)

        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()

    # ADD NETWORK GROUP
    def create_group(
        self,
        pGroupId: int,
        name: str,
        group_type: str,
        timezone: str = None,
        description: str = None,
        latitude: float = None,
        longitude: float = None,
        businessType: str = None
    ):
        url = f"{self.BASE_URL}/service/api/open/v1/group"
        params = {"access_token": self.access_token}

        payload = {
            "pGroupId": pGroupId,
            "name": name,
            "type": group_type
        }

        # optional fields
        if timezone:
            payload["timezone"] = timezone
        if description:
            payload["description"] = description
        if latitude:
            payload["latitude"] = latitude
        if longitude:
            payload["longitude"] = longitude
        if businessType:
            payload["businessType"] = businessType

        res = requests.post(
            url,
            params=params,
            json=payload,
            timeout=10
        )
        res.raise_for_status()
        return res.json()